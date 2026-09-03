import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))

from datetime import datetime
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-04_fisher_transform_extreme_cross.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

qqq = load_equity("QQQ", datetime(2019,1,1), datetime(2026,9,1))
t0=time.time()
pos = strat.generate_signals(qqq, window=10, extreme_threshold=1.5)
print("time:", time.time()-t0, "sanity trades", (pos.diff()==1).sum())
