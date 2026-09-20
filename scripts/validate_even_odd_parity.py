import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-21_even_odd_calendar_day_parity.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
symbol = "SPY"
best_params = {"long_parity": "odd"}

df = load_equity(symbol, start, end)
returns = strat.generate_returns(df, **best_params)

results = {}

passed, ev = check_sharpe_ratio(returns, min_sharpe=1.0)
results["sharpe_ratio"] = ev
print("sharpe:", passed, ev)

passed, ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["max_drawdown"] = ev
print("mdd:", passed, ev)

position = strat.generate_signals(df, **best_params)
num_trades = int((position.diff().abs() == 1).sum())
passed, ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades, min_net_sharpe=0.5)
results["transaction_cost_survival"] = ev
print("tc survival:", passed, ev)

def strat_fn(slice_df):
    return strat.generate_returns(slice_df, **best_params)

passed, ev = check_walk_forward(df, strat_fn, n_splits=4, min_pass_fraction=0.75)
results["walk_forward"] = ev
print("walk forward:", passed, ev)

# param sensitivity from the two long_parity variants' full-sample Sharpe
grid_results = {}
for parity in ["even", "odd"]:
    r = strat.generate_returns(df, long_parity=parity)
    import vectorbt as vbt
    sh = r.vbt.returns(freq="D").sharpe_ratio()
    grid_results[f"long_parity={parity}"] = float(sh) if sh is not None else 0.0

passed, ev = check_parameter_sensitivity(grid_results, max_relative_std=0.5)
results["parameter_sensitivity"] = ev
print("param sensitivity:", passed, ev)

with open("/tmp/even_odd_parity_validators.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
