import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "shooting_star", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_shooting_star_rsi_short_reversal.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_crypto, load_equity
from validators import check_sharpe_ratio, check_max_drawdown

for asset_fn, sym in [(load_crypto, "BTC/USDT"), (load_equity, "QQQ"), (load_equity, "SPY")]:
    df = asset_fn(sym, start=datetime(2018,1,1), end=datetime(2026,9,1))
    params = dict(trend_window=75, shadow_ratio=2.0, rsi_overbought=65.0)
    rets = strat.generate_returns(df, **params)
    sharpe, ev = check_sharpe_ratio(rets)
    mdd, evm = check_max_drawdown(rets)
    n_trades = int((rets != 0).sum())
    print(sym, "sharpe", ev, "mdd", evm, "nonzero_days", n_trades)
