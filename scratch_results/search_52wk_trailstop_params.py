import sys, os, json, itertools
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "wk52ts", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_52wk_high_trailing_stop_exit.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio, check_max_drawdown

df_spy = load_equity("SPY", start=datetime(2018,1,1), end=datetime(2026,9,1))
df_qqq = load_equity("QQQ", start=datetime(2018,1,1), end=datetime(2026,9,1))

best = None
for lb, trail in itertools.product([63, 100, 126, 189, 252], [0.10, 0.15, 0.20, 0.25, 0.30]):
    params = dict(lookback_days=lb, trail_pct=trail)
    r_spy = strat.generate_returns(df_spy, **params)
    r_qqq = strat.generate_returns(df_qqq, **params)
    sh_spy = check_sharpe_ratio(r_spy)[1]["value"]
    sh_qqq = check_sharpe_ratio(r_qqq)[1]["value"]
    combined = min(sh_spy or -99, sh_qqq or -99)
    if best is None or combined > best[0]:
        best = (combined, params, sh_spy, sh_qqq)

print("BEST", best)
