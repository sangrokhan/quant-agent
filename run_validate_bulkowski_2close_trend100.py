import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

import importlib.util
from datetime import datetime
import json

spec = importlib.util.spec_from_file_location("bulk2c_strat", "strategies/2026-09-28_bulkowski_2close_bullish_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

# Light rescue attempt: shorter trend_window (100 instead of 200) to admit
# more trades without abandoning the trend-filter concept entirely.
results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end, interval="1d")
    params = {"trend_window": 100, "target_height_mult": 2.0, "max_hold_days": 25}
    returns = strat.generate_returns(price_df, **params)
    sig = strat.generate_signals(price_df, **params)
    num_trades = int((sig.diff().abs() == 1).sum())
    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)
    results[symbol] = {"num_trades": num_trades, "sharpe": sharpe_ev, "mdd": mdd_ev, "tc": tc_ev}

print(json.dumps(results, indent=2, default=str))
with open("validate_result_bulkowski_2close_trend100.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
