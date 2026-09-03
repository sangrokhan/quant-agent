import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))

from datetime import datetime
from loaders import load_equity
from validators import check_sharpe_ratio
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-04_fisher_transform_extreme_cross.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
qqq = load_equity("QQQ", start, end)
spy = load_equity("SPY", start, end)

combos = [{"window": w, "extreme_threshold": t} for w in [8,10,14] for t in [1.0,1.5]]
for label, df in [("QQQ", qqq), ("SPY", spy)]:
    print(f"--- {label} ---")
    for c in combos:
        ret = strat.generate_returns(df, **c)
        pos = strat.generate_signals(df, **c)
        n = int((pos.diff()==1).sum())
        _, ev = check_sharpe_ratio(ret, min_sharpe=1.0)
        print(label, c, "sharpe=", round(ev["value"],3) if ev["value"] is not None else None, "trades=", n)
