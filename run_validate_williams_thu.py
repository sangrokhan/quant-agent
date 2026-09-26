import sys, json
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("wodtdw", "strategies/2026-09-26_williams_outside_day_tdw_reversal.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2019,1,1), datetime(2026,9,1)
for sym in ["QQQ","SPY"]:
    df = load_equity(sym, start=start, end=end)
    params = dict(exclude_weekday=3, max_hold_days=15)
    rets = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    num_trades = int((pos.diff().abs()==1).sum())
    sharpe = check_sharpe_ratio(rets)
    print(sym, sharpe, num_trades)
