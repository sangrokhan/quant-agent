import sys, json
from datetime import datetime
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_ema_pullback_rsi_macd_stack.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward

df = load_equity("QQQ", datetime(2017, 1, 1), datetime(2026, 9, 1))
params = dict(pullback_band=0.012, rsi_low=35.0)
returns = strat.generate_returns(df, **params)

sharpe = check_sharpe_ratio(returns)
mdd = check_max_drawdown(returns)
sig = strat.generate_signals(df, **params)
num_trades = int((sig.diff() == 1).sum())
tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
wf = check_walk_forward(df, lambda pdf: strat.generate_returns(pdf, **params))

out = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf}
print(json.dumps(out, indent=2, default=str))
with open("validators_ema_pullback_stack.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
