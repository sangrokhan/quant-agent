import sys, json
from datetime import datetime
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_williams_r_oversold_trend_gated.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity

df = load_equity("QQQ", datetime(2017, 1, 1), datetime(2026, 9, 1))
params = dict(oversold_threshold=-90.0, trend_window=100, exit_threshold=-30.0)
returns = strat.generate_returns(df, **params)

sharpe = check_sharpe_ratio(returns)
mdd = check_max_drawdown(returns)
sig = strat.generate_signals(df, **params)
num_trades = int((sig.diff() == 1).sum())
tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

# check_walk_forward relies on a vectorbt API (vbt.utils.splitting.RangeSplitter)
# that's absent in the installed vectorbt version; do a manual 4-split
# walk-forward with the same semantics (per-split Sharpe > 0, pass_fraction
# threshold 0.75) instead of leaving walk-forward untested.
import vectorbt as vbt
n_splits = 4
idx = df.index
step = len(idx) // n_splits
wf_results = []
for i in range(n_splits):
    s = i * step
    e = len(idx) if i == n_splits - 1 else (i + 1) * step
    slice_df = df.iloc[s:e]
    if slice_df.empty:
        continue
    r = strat.generate_returns(slice_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
wf = (bool(wf_pass_fraction >= 0.75), {
    "metric": "walk_forward_pass_fraction",
    "value": wf_pass_fraction,
    "threshold": 0.75,
    "n_splits": n_splits,
    "per_split_passed": wf_results,
    "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)",
})

# param sensitivity from grid json (already computed cells for QQQ)
import json as _json
with open("grid_result_williams_trend.json") as f:
    grid_summary = _json.load(f)

# Rebuild per-config sharpe map for QQQ specifically from a quick param sweep
from itertools import product
param_grid_results = {}
for ot, tw, et in product([-90.0, -95.0], [100, 200], [-50.0, -30.0]):
    r = strat.generate_returns(df, oversold_threshold=ot, trend_window=tw, exit_threshold=et)
    sh = check_sharpe_ratio(r)[1]["value"]
    param_grid_results[f"ot={ot},tw={tw},et={et}"] = sh if sh is not None else 0.0

psens = check_parameter_sensitivity(param_grid_results)

out = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "param_sensitivity": psens, "num_trades": num_trades}
print(json.dumps(out, indent=2, default=str))
with open("validators_williams_trend.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
