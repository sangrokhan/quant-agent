import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from loaders import load_equity
import importlib.util

spec_path = "strategies/2026-09-23_atr_liquidity_sweep_horizon_confirm.py"
mspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival

start, end = datetime(2019,1,1), datetime(2026,9,1)
best_params = dict(swing_window=20, poke_atr_mult=0.3, confirm_bars=3)

price_df = load_equity("SPY", start, end, interval="1d")
returns = strat.generate_returns(price_df, **best_params)
positions = strat.generate_signals(price_df, **best_params)
num_trades = int((positions.diff() == 1).sum())

sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_p, mdd_e = check_max_drawdown(returns, max_allowed_mdd=0.25)
tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

print(json.dumps({"num_trades": num_trades, "sharpe": sharpe_e, "sharpe_passed": sharpe_p,
                   "mdd": mdd_e, "mdd_passed": mdd_p, "tc": tc_e, "tc_passed": tc_p}, indent=2, default=str))
