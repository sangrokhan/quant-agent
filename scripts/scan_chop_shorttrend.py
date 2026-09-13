import sys, os, json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data"))
sys.path.insert(0, os.path.join(ROOT, "validation"))

from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio
import importlib.util

spec_path = os.path.join(ROOT, "strategies", "2026-09-13_chop_sizing_shorttrend_deadband.py")
spec = importlib.util.spec_from_file_location("chop_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2017, 1, 1), datetime(2026, 9, 1)

candidates = [
    {"trend_window": 40, "chop_sensitivity": 0.5, "deadband": 0.10},
    {"trend_window": 25, "chop_sensitivity": 0.5, "deadband": 0.15},
    {"trend_window": 30, "chop_sensitivity": 0.5, "deadband": 0.10},
    {"trend_window": 40, "chop_sensitivity": 0.7, "deadband": 0.10},
    {"trend_window": 40, "chop_sensitivity": 0.5, "deadband": 0.15},
    {"trend_window": 40, "chop_sensitivity": 0.5, "deadband": 0.20},
]

for params in candidates:
    print("=== params:", params)
    for symbol in ["QQQ", "SPY"]:
        price_df = load_equity(symbol, start, end)
        returns = strat.generate_returns(price_df, **params)
        sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
        print(symbol, "sharpe", round(sharpe_e["value"], 3), sharpe_p)
