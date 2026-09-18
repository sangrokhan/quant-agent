import importlib.util, sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-18_four_up_days_hold_to_friday.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)
import vectorbt as vbt
from loaders import load_crypto
start = datetime(2018,1,1)
end = datetime(2026,9,1)
for sym in ["BTC/USDT","ETH/USDT"]:
    df = load_crypto(sym, start, end)
    for sl in [3,4,5]:
        r = strat.generate_returns(df, streak_len=sl)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        mdd = abs(r.vbt.returns(freq="D").max_drawdown())
        print(sym, sl, sh, mdd)
