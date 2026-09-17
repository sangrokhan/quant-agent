import sys, os, json
from datetime import datetime
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-17_ath_chandelier_volgate.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto

spec = GridSpec(
    param_grid={
        "atr_multiplier": [2.5, 3.0, 4.0],
        "vol_regime_ratio": [0.9, 1.0, 1.2],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_result_ath_chandelier_volgate.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
