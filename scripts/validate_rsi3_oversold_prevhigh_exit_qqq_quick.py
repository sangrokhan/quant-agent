import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from data.loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-18_rsi3_oversold_prevhigh_exit.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

price = load_equity("QQQ", datetime(2015,1,1), datetime(2026,9,1))

params = dict(rsi_oversold=20, max_hold_days=10)
returns = strat.generate_returns(price, **params)
signals = strat.generate_signals(price, **params)
num_trades = int((signals.diff() == 1).sum())

results = {}
results["sharpe"] = check_sharpe_ratio(returns)
results["mdd"] = check_max_drawdown(returns)
results["tc_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
results["num_trades"] = num_trades
print(json.dumps(results, indent=2, default=str))
