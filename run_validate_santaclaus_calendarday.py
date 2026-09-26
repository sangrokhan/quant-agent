import sys, json
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("santa", "strategies/2026-09-26_santaclaus_calendarday_entry.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2019,1,1), datetime(2026,9,1)
results = {}
params = dict(entry_calendar_day=15, exit_trading_day_jan=2)
for sym in ["BTC/USDT", "ETH/USDT", "QQQ", "SPY"]:
    if "/" in sym:
        df = load_crypto(sym, start=start, end=end)
    else:
        df = load_equity(sym, start=start, end=end)
    rets = strat.generate_returns(df, **params)
    num_trades = int((strat.generate_signals(df, **params).diff().abs() == 1).sum())
    sharpe = check_sharpe_ratio(rets)
    mdd = check_max_drawdown(rets)
    tc = check_transaction_cost_survival(rets, cost_bps_per_trade=10.0, num_trades=num_trades)
    results[sym] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "num_trades": num_trades}

print(json.dumps(results, indent=2, default=str))
with open("validate_result_santaclaus_calendarday.json","w") as f:
    json.dump(results, f, indent=2, default=str)
