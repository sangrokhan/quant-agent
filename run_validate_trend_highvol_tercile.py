import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_trend_highvol_tercile_gate.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

SYMBOL = "SPY"
PARAMS = {"trend_window": 50, "vol_percentile_floor": 0.75}

price_df = load_equity(SYMBOL, start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
returns = strat.generate_returns(price_df, **PARAMS)
signals = strat.generate_signals(price_df, **PARAMS)
num_trades = int((signals.diff().fillna(0) == 1).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)

def strat_fn(slice_df):
    return strat.generate_returns(slice_df, **PARAMS)

df_idx = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
try:
    results["walk_forward"] = check_walk_forward(
        df_idx, lambda slice_df: strat.generate_returns(slice_df.reset_index(), **PARAMS),
        n_splits=4, min_pass_fraction=0.75,
    )
except AttributeError:
    import vectorbt as vbt  # noqa
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
        r = strat.generate_returns(slice_df, **PARAMS)
        sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sharpe is not None and sharpe > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    results["walk_forward"] = (pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable)",
    })

# Parameter sensitivity: derive from grid summary (reuse the grid cells for SPY high vol regime)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from grid_test import run_strategy_grid, GridSpec
grid_spec = GridSpec(
    param_grid={"trend_window": [40, 50, 60], "vol_percentile_floor": [0.667, 0.75, 0.8]},
    symbols={"equity": ["SPY"]},
    vol_regime_splits=3,
)
from loaders import load_equity as _le, load_crypto as _lc
grid_result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": _le, "crypto": _lc},
    spec=grid_spec, start=datetime(2018, 1, 1), end=datetime(2026, 9, 1),
)
param_grid_results = {}
for c in grid_result.cells:
    if c.vol_regime_label == "high" and c.sharpe is not None:
        key = f"{c.params}"
        param_grid_results[key] = c.sharpe

results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
print(json.dumps(out, indent=2, default=str))
with open("validate_result_trend_highvol_tercile_spy.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
