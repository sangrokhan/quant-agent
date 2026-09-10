import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_vwap_stdev_band_rotation.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival
import vectorbt as vbt

start = datetime(2017, 1, 1)
end = datetime(2026, 9, 1)
best_params = dict(vwap_window=20, dev_mult=1.0)

results = {}
for symbol in ["QQQ", "SPY"]:
    df = load_equity(symbol, start, end)
    returns = strat.generate_returns(df, **best_params)
    sig = strat.generate_signals(df, **best_params)
    num_trades = int((sig.diff().fillna(0) != 0).sum() / 2) + 1
    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    results[symbol] = {"num_trades": num_trades, "sharpe": sharpe_ev, "mdd": mdd_ev, "tc": tc_ev}

print(json.dumps(results, indent=2, default=str))
