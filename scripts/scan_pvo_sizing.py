import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime
from itertools import product

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-14_pvo_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown

df_qqq = load_equity("QQQ", datetime(2017,1,1), datetime(2026,9,1), interval="1d")
df_spy = load_equity("SPY", datetime(2017,1,1), datetime(2026,9,1), interval="1d")

for fs, be, se in product([12,20],[0.4,0.6,0.8],[0.5,0.7,0.9]):
    rq = strat.generate_returns(df_qqq, fast_span=fs, base_exposure=be, sensitivity=se)
    sh_q = check_sharpe_ratio(rq)[1]["value"]
    mdd_q = check_max_drawdown(rq)[1]["value"]
    rs = strat.generate_returns(df_spy, fast_span=fs, base_exposure=be, sensitivity=se)
    sh_s = check_sharpe_ratio(rs)[1]["value"]
    mdd_s = check_max_drawdown(rs)[1]["value"]
    print(f"fs={fs} be={be} se={se}: QQQ sharpe={sh_q:.3f} mdd={mdd_q:.3f} | SPY sharpe={sh_s:.3f} mdd={mdd_s:.3f}")
