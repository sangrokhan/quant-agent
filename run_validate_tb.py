import sys, os, json
from datetime import datetime
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_equity

spec = importlib.util.spec_from_file_location(
    "tb_strat", "strategies/2026-09-28_triple_barrier_donchian_volscaled_exit.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

best_params = dict(theta_up=3.0, theta_dn=1.5, max_hold_days=20)

df = load_equity("QQQ", datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df

returns = strat.generate_returns(df, **best_params)
pos = strat.generate_signals(df, **best_params)
num_trades = int((pos.diff().fillna(0) != 0).sum() / 2) + 1

evidence = {}
evidence["sharpe"] = check_sharpe_ratio(returns, min_sharpe=1.0)
evidence["mdd"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
evidence["tc_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)

try:
    evidence["walk_forward"] = check_walk_forward(
        df_idx, lambda slice_df: strat.generate_returns(slice_df.reset_index(), **best_params),
        n_splits=4, min_pass_fraction=0.75,
    )
except AttributeError:
    n_splits = 4
    pdf_sorted = df_idx.sort_index()
    chunk_len = len(pdf_sorted) // n_splits
    wf_results = []
    for i in range(n_splits):
        lo = i * chunk_len
        hi = len(pdf_sorted) if i == n_splits - 1 else (i + 1) * chunk_len
        slice_df = pdf_sorted.iloc[lo:hi].reset_index()
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **best_params)
        import vectorbt as vbt  # noqa
        sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sharpe is not None and sharpe > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    evidence["walk_forward"] = (pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split",
    })

# parameter sensitivity from the grid results
summary = json.load(open("/tmp/tb_grid_summary.json"))
grid_shape_pass_frac = summary["pass_fraction"]
evidence["param_sensitivity_from_grid"] = {
    "note": "using grid pass_fraction as a proxy for parameter sensitivity",
    "grid_pass_fraction": grid_shape_pass_frac,
    "by_asset_class": summary["by_asset_class"],
    "by_vol_regime": summary["by_vol_regime"],
}

print(json.dumps({k: (v if not isinstance(v, tuple) else [v[0], v[1]]) for k, v in evidence.items()}, indent=2, default=str))

with open("/tmp/tb_validators.json", "w") as f:
    json.dump({k: (v if not isinstance(v, tuple) else [v[0], v[1]]) for k, v in evidence.items()}, f, indent=2, default=str)
