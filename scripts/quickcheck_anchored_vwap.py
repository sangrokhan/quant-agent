import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from validators import check_sharpe_ratio, check_max_drawdown
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-09_anchored_vwap_reclaim.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
best_params = dict(anchor_window=60, touch_tolerance=0.02, max_hold_days=30)

for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **best_params)
    signals = strat.generate_signals(price_df, **best_params)
    num_trades = int((signals.diff().fillna(0) == 1).sum())
    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    print(symbol, "trades:", num_trades, "sharpe:", sharpe_ev["value"], sharpe_p, "mdd:", mdd_ev["value"], mdd_p)
