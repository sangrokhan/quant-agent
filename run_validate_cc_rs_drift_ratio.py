import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_equity
import importlib.util

spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-21_cc_rs_drift_ratio_trend_breakout.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

BEST_PARAMS = dict(ratio_threshold=1.3, breakout_window=15)
SYM = "SPY"

price_df = load_equity(SYM, start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
returns = strat.generate_returns(price_df, **BEST_PARAMS)
signals = strat.generate_signals(price_df, **BEST_PARAMS)
num_trades = int((signals.diff() == 1).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)

grid_cells = json.load(open("grid_cells_cc_rs_drift_ratio.json"))
param_sharpes = {}
for c in grid_cells:
    if c["symbol"] == SYM and c["sharpe"] is not None:
        key = str(c["params"])
        param_sharpes.setdefault(key, []).append(c["sharpe"])
param_sharpes_avg = {k: sum(v) / len(v) for k, v in param_sharpes.items()}
results["parameter_sensitivity"] = check_parameter_sensitivity(param_sharpes_avg, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
out["num_trades"] = num_trades
print(json.dumps(out, indent=2, default=str))
with open("validation_cc_rs_drift_ratio.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
