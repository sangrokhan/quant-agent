import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

import importlib.util
from loaders import load_equity

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-08_atr_breakout_overnight_carry_gate.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

df = load_equity("QQQ", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
r = strat.generate_returns(df, atr_mult=0.25, atr_period=20)
sig = strat.generate_signals(df, atr_mult=0.25, atr_period=20)
print("num breakout days:", int(sig.sum()), "/", len(sig))
print("fraction negative returns on breakout days:", ((r[sig.astype(bool)] < 0).mean()))
print("mean intraday-only return check")
open_ = df["open"]; close = df["close"]
intraday_ret = (close/open_ - 1.0)
print("min intraday ret on breakout days:", intraday_ret[sig.astype(bool)].min())
print("any negative intraday leg on breakout day?", (intraday_ret[sig.astype(bool)] < 0).any())
