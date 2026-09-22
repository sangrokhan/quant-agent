import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from loaders import load_equity, load_crypto
import importlib.util
import itertools
import vectorbt as vbt

spec_path = "strategies/2026-09-23_yield_curve_steepening_trend_gate.py"
mspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

start, end = datetime(2019,1,1), datetime(2026,9,1)
grid = {
    "fast_window": [10,20],
    "slope_percentile": [0.2,0.35],
    "confirm_window": [10,20],
}
combos = list(itertools.product(*grid.values()))
names = list(grid.keys())

for asset, symbols, loader in [("equity", ["QQQ","SPY"], load_equity), ("crypto", ["BTC/USDT","ETH/USDT"], load_crypto)]:
    for sym in symbols:
        try:
            price_df = loader(sym, start, end, interval="1d")
        except TypeError:
            price_df = loader(sym, start, end)
        best = None
        for combo in combos:
            params = dict(zip(names, combo))
            r = strat.generate_returns(price_df, **params)
            if r.abs().sum() == 0:
                continue
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            if sh is None:
                continue
            if best is None or sh > best[0]:
                best = (sh, params)
        print(asset, sym, best)
