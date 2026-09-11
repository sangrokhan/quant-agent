import sys, os, json, functools
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-11_sector_momentum_rank_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec, GridResult
from loaders import load_equity, load_crypto

param_grid = {
    "trend_sma_window": [50, 100],
    "momentum_window": [126, 252],
    "rank_threshold": [3, 5],
}

symbols = {"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}
loaders = {"equity": load_equity, "crypto": load_crypto}

combined = GridResult()
for asset_class, syms in symbols.items():
    for sym in syms:
        def wrapped_returns_fn(price_df, _sym=sym, _ac=asset_class, **params):
            return strat.generate_returns(price_df, primary_symbol=_sym, asset_class=_ac, **params)

        single_spec = GridSpec(
            param_grid=param_grid,
            symbols={asset_class: [sym]},
            vol_regime_splits=3,
        )
        result = run_strategy_grid(
            generate_returns_fn=wrapped_returns_fn,
            loader_fn_by_asset_class=loaders,
            spec=single_spec,
            start=datetime(2017, 1, 1),
            end=datetime(2026, 9, 1),
        )
        combined.cells.extend(result.cells)

summary = combined.summary()
with open("grid_result_sector_momentum.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
