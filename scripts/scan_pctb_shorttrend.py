import sys, os, json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data"))
sys.path.insert(0, os.path.join(ROOT, "validation"))

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util
from functools import partial

spec_path = os.path.join(ROOT, "strategies", "2026-09-13_percent_b_sizing_shorttrend.py")
spec = importlib.util.spec_from_file_location("pctb_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2017, 1, 1), datetime(2026, 9, 1)

candidates = [
    {"trend_window": 35, "pb_sensitivity": 0.4, "bb_std": 2.0},
    {"trend_window": 35, "pb_sensitivity": 0.3, "bb_std": 2.0},
    {"trend_window": 35, "pb_sensitivity": 0.5, "bb_std": 2.0},
    {"trend_window": 32, "pb_sensitivity": 0.4, "bb_std": 2.0},
    {"trend_window": 45, "pb_sensitivity": 0.4, "bb_std": 2.0},
    {"trend_window": 30, "pb_sensitivity": 0.3, "bb_std": 2.0},
    {"trend_window": 45, "pb_sensitivity": 0.6, "bb_std": 2.0},
]

for params in candidates:
    print("=== params:", params)
    for symbol in ["QQQ", "SPY"]:
        price_df = load_equity(symbol, start, end)
        returns = strat.generate_returns(price_df, **params)
        sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
        print(symbol, "sharpe", round(sharpe_e["value"], 3), sharpe_p)

report = {}
best_params = {"trend_window": 40, "pb_sensitivity": 0.4, "bb_std": 2.0}  # placeholder, will refine after seeing above
