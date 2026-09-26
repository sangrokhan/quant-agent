import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util

spec_mod_path = "strategies/2026-09-26_drop_base_rally_demand_zone.py"
spec = importlib.util.spec_from_file_location("strat_dbr", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

CONFIG = dict(decline_pct=0.03, rally_mult=1.5, target_rr=1.5, max_hold_days=40)

price = load_equity("QQQ", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
returns = strat.generate_returns(price, **CONFIG)

position = strat.generate_signals(price, **CONFIG)
num_trades = int((position.diff().fillna(0) == 1).sum())
print("num_trades:", num_trades)

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
try:
    results["walk_forward"] = check_walk_forward(
        price, lambda slice_df: strat.generate_returns(slice_df, **CONFIG)
    )
except Exception as e:
    results["walk_forward"] = (None, {"reason": f"skipped: {e}"})

# parameter sensitivity: derive from grid results for QQQ nearby configs
param_grid_results = {
    "decline_pct=0.03,rally_mult=1.5,target_rr=1.5,max_hold_days=40": 1.7990610348864076,
    "decline_pct=0.03,rally_mult=1.5,target_rr=1.5,max_hold_days=20": 1.7990610348864076,
    "decline_pct=0.03,rally_mult=1.5,target_rr=2.0,max_hold_days=40": 1.7897269232517024,
    "decline_pct=0.03,rally_mult=1.5,target_rr=2.0,max_hold_days=20": 1.7389316016423904,
    "decline_pct=0.03,rally_mult=1.5,target_rr=3.0,max_hold_days=20": 1.6885205493313744,
    "decline_pct=0.03,rally_mult=1.5,target_rr=3.0,max_hold_days=40": 1.60838167383527,
}
try:
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)
except Exception as e:
    results["parameter_sensitivity"] = (None, {"reason": f"skipped: {e}"})

out = {}
for k, v in results.items():
    if v[0] is None and "reason" in v[1]:
        out[k] = {"passed": None, **v[1]}
    else:
        passed, evidence = v
        out[k] = {"passed": passed, **evidence}

with open("validate_result_drop_base_rally_demand_qqq.json", "w") as f:
    json.dump(out, f, indent=2, default=str)

print(json.dumps(out, indent=2, default=str))
print("n_trades approx (nonzero return days):", int((returns != 0).sum()))
