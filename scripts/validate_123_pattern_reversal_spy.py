import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from data.loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-18_123_pattern_reversal.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

price = load_equity("SPY", datetime(2015,1,1), datetime(2026,9,1))

params = dict(max_hold_days=30)
returns = strat.generate_returns(price, **params)
signals = strat.generate_signals(price, **params)
num_trades = int((signals.diff() == 1).sum())

results = {}
results["sharpe"] = check_sharpe_ratio(returns)
results["mdd"] = check_max_drawdown(returns)
results["tc_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

n_splits = 4
idx = price.index
step = len(idx) // n_splits
wf_results = []
for i in range(n_splits):
    s = i * step
    e = len(idx) if i == n_splits - 1 else (i + 1) * step
    slice_df = price.iloc[s:e]
    if slice_df.empty:
        continue
    r = strat.generate_returns(slice_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
results["walk_forward"] = (bool(wf_pass_fraction >= 0.75), {
    "metric": "walk_forward_pass_fraction",
    "value": wf_pass_fraction,
    "threshold": 0.75,
    "n_splits": n_splits,
    "per_split_passed": wf_results,
    "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable)",
})

cells = json.load(open("grid_cells_123_pattern_reversal.json"))
spy_cells = [c for c in cells if c["symbol"]=="SPY" and c["asset_class"]=="equity"]
pg = {str(c["params"]): c["sharpe"] for c in spy_cells if c["sharpe"] is not None}
results["param_sensitivity"] = check_parameter_sensitivity(pg)

results["num_trades"] = num_trades
print(json.dumps(results, indent=2, default=str))
with open("validate_result_123_pattern_reversal_spy.json","w") as f:
    json.dump(results, f, indent=2, default=str)
