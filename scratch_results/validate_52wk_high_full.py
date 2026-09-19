import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "wk52", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_52wk_high_breakout_sma_exit.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_crypto, load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity

params = dict(lookback_days=126, exit_sma_window=100)

for asset_fn, sym in [(load_equity, "QQQ"), (load_equity, "SPY"), (load_crypto, "BTC/USDT"), (load_crypto, "ETH/USDT")]:
    df = asset_fn(sym, start=datetime(2018,1,1), end=datetime(2026,9,1))
    rets = strat.generate_returns(df, **params)
    sharpe, ev = check_sharpe_ratio(rets)
    mdd, evm = check_max_drawdown(rets)
    n_trades_approx = int((rets.shift(-1) != rets).sum())
    print(sym, json.dumps(ev), json.dumps(evm), "n_nonzero_days", int((rets!=0).sum()))
