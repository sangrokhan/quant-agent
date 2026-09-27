import sys, os, json, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
from datetime import datetime

spec = importlib.util.spec_from_file_location(
    "va_engulf_strat", os.path.join(os.path.dirname(__file__), "strategies", "2026-09-27_value_area_engulfing_reclaim.py")
)
strat = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_walk_forward,
    check_parameter_sensitivity,
)

params = dict(lookback=15, vol_mult=1.2, max_hold_days=6)
df = load_equity("SPY", datetime(2019, 1, 1), datetime(2026, 9, 1))
returns = strat.generate_returns(df, **params)
positions = strat.generate_signals(df, **params)
num_trades = int((positions.diff().fillna(0) == 1).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)
try:
    results["walk_forward"] = check_walk_forward(
        df, lambda pdf: strat.generate_returns(pdf, **params), n_splits=4
    )
except Exception as exc:
    # Known repo issue: vectorbt's RangeSplitter API is unavailable in the
    # installed vectorbt version. Fall back to a manual 4-fold walk-forward
    # (equal contiguous date splits, positive-Sharpe pass criterion) so the
    # validator still yields a real judgement rather than being skipped.
    import numpy as np
    n_splits = 4
    idx = df.index if "timestamp" not in df.columns else df.set_index("timestamp").index
    split_edges = np.linspace(0, len(idx), n_splits + 1, dtype=int)
    per_split_passed = []
    for i in range(n_splits):
        lo, hi = split_edges[i], split_edges[i + 1]
        if hi - lo < 30:
            continue
        slice_df = df.iloc[lo:hi]
        r = strat.generate_returns(slice_df, **params)
        try:
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
        except Exception:
            sh = None
        per_split_passed.append(bool(sh is not None and sh > 0))
    pass_fraction = (sum(per_split_passed) / len(per_split_passed)) if per_split_passed else 0.0
    results["walk_forward"] = (
        bool(pass_fraction >= 0.75),
        {
            "metric": "walk_forward_pass_fraction",
            "value": pass_fraction,
            "threshold": 0.75,
            "n_splits": n_splits,
            "per_split_passed": per_split_passed,
            "note": f"manual fallback split (vectorbt RangeSplitter API error: {exc})",
        },
    )

param_grid_results = {}
for lb in [15, 20, 30]:
    for vm in [1.2, 1.5]:
        p = dict(lookback=lb, vol_mult=vm, max_hold_days=6)
        r = strat.generate_returns(df, **p)
        try:
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
        except Exception:
            sh = None
        param_grid_results[str(p)] = float(sh) if sh is not None else 0.0

results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)

out = {}
for k, v in results.items():
    passed, evidence = v
    out[k] = {"passed": passed, "evidence": evidence}

with open("validators_value_area_engulfing_reclaim_spy.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
