import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

spec_mod_path = "strategies/2026-09-22_composite_momentum_absolute_gate.py"
spec = importlib.util.spec_from_file_location("strat_cm", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

price_df = load_equity("QQQ", start, end)
params = dict(w3=0.5, w12=2.0, w6=1.0, rebalance_days=21)

returns = strat.generate_returns(price_df, **params)

import functools
strategy_fn = functools.partial(strat.generate_returns, **params)

signals = strat.generate_signals(price_df, **params)
num_trades = int((signals.diff().abs() == 1).sum())

out = {}
out["sharpe_ratio"] = check_sharpe_ratio(returns)
out["max_drawdown"] = check_max_drawdown(returns)
out["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
try:
    out["walk_forward"] = check_walk_forward(price_df, strategy_fn)
except Exception as e:
    out["walk_forward"] = (None, {"error": str(e)})

# parameter sensitivity from grid results
grid_cells = json.load(open("grid_cells_composite_momentum_absolute_gate.json"))
qqq_cells = [c for c in grid_cells if c["symbol"] == "QQQ"]
param_grid_results = {}
for c in qqq_cells:
    key = json.dumps(c["params"], sort_keys=True)
    param_grid_results.setdefault(key, []).append(c["sharpe"])
avg_by_param = {k: sum(v)/len(v) for k, v in param_grid_results.items()}
try:
    out["parameter_sensitivity"] = check_parameter_sensitivity(avg_by_param)
except Exception as e:
    out["parameter_sensitivity"] = (None, {"error": str(e), "avg_by_param": avg_by_param})

def ser(o):
    if isinstance(o, tuple):
        return [ser(o[0]), o[1]]
    return o

print(json.dumps({k: ser(v) for k, v in out.items()}, indent=2, default=str))

with open("validate_result_composite_momentum_qqq.json", "w") as f:
    json.dump({k: ser(v) for k, v in out.items()}, f, indent=2, default=str)
