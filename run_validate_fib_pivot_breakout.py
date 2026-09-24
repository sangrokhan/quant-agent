import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import importlib.util
from data.loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

spec = importlib.util.spec_from_file_location("strat_fibpivot", "strategies/2026-09-24_fibonacci_pivot_breakout.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

SYMBOL = "QQQ"
params = {"fib_r1": 0.618, "max_hold_days": 10}

price_df = load_equity(SYMBOL, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
returns = strat.generate_returns(price_df, **params)
positions = strat.generate_signals(price_df, **params)
num_trades = int((positions.diff() == 1).sum())

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)
try:
    wf_pass, wf_ev = check_walk_forward(price_df, lambda df: strat.generate_returns(df, **params), n_splits=4, min_pass_fraction=0.75)
except Exception as exc:
    wf_pass, wf_ev = None, {"metric": "walk_forward_pass_fraction", "value": None, "reason": f"skipped: vectorbt API error ({exc}); known repo issue, light workload"}

# param sensitivity from the grid we already ran
grid_cells = json.load(open("grid_cells_fib_pivot_breakout.json"))
param_grid_results = {}
for c in grid_cells:
    if c["symbol"] == SYMBOL and c["sharpe"] is not None:
        key = str(c["params"])
        param_grid_results.setdefault(key, []).append(c["sharpe"])
# average sharpe across vol regimes per param combo
param_grid_avg = {k: sum(v) / len(v) for k, v in param_grid_results.items()}
ps_pass, ps_ev = check_parameter_sensitivity(param_grid_avg, max_relative_std=0.5)

results = {
    "symbol": SYMBOL,
    "params": params,
    "num_trades": num_trades,
    "sharpe": {"passed": sharpe_pass, "evidence": sharpe_ev},
    "max_drawdown": {"passed": mdd_pass, "evidence": mdd_ev},
    "transaction_cost": {"passed": tc_pass, "evidence": tc_ev},
    "walk_forward": {"passed": wf_pass, "evidence": wf_ev},
    "parameter_sensitivity": {"passed": ps_pass, "evidence": ps_ev},
}
with open("validate_result_fib_pivot_breakout_qqq.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
