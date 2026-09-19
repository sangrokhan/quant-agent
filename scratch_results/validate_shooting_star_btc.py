import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "shooting_star", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_shooting_star_rsi_short_reversal.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward

df = load_crypto("BTC/USDT", start=datetime(2018,1,1), end=datetime(2026,9,1))
params = dict(trend_window=75, shadow_ratio=2.0, rsi_overbought=65.0)

sharpe = check_sharpe_ratio(strat.generate_returns, df, params=params)
mdd = check_max_drawdown(strat.generate_returns, df, params=params)
tc = check_transaction_cost_survival(strat.generate_returns, df, params=params)
wf = check_walk_forward(strat.generate_returns, df, params=params)

out = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf}
print(json.dumps(out, indent=2, default=str))
