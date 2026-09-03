import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))

from datetime import datetime
from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-04_fisher_transform_extreme_cross.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

spec = GridSpec(
    param_grid={"window": [8, 10, 14], "extreme_threshold": [1.0, 1.5]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
