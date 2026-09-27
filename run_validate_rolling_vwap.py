import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival
from data.loaders import load_equity
import importlib.util
import vectorbt as vbt

spec = importlib.util.spec_from_file_location("strat_vwapmr", "strategies/2026-09-27_rolling_vwap_meanrev_adx_regime.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(vwap_window=20, std_mult=1.5, adx_threshold=35.0)
price = load_equity("SPY", start=datetime(2019,1,1), end=datetime(2026,9,1))
returns = strat.generate_returns(price, **params)
signals = strat.generate_signals(price, **params)
num_trades = int((signals.diff() == 1).sum())

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
mdd_pass, mdd_ev = check_max_drawdown(returns)
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades)

evidence = {"num_trades": num_trades, "sharpe": sharpe_ev, "sharpe_pass": sharpe_pass, "mdd": mdd_ev, "mdd_pass": mdd_pass, "tc": tc_ev, "tc_pass": tc_pass}
print(json.dumps(evidence, indent=2, default=str))
