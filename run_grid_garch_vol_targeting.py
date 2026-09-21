import sys
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, "strategies")

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-21_garch_vol_targeting_continuous_sizing.py"
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

spec = GridSpec(
    param_grid={
        "vol_target": [0.10, 0.15, 0.20],
        "refit_every": [42],
        "leverage_cap": [1.0, 1.5],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
print("starting grid", flush=True)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)
print("grid done", flush=True)
summary = result.summary()
import json
with open("grid_summary_garch_vol_targeting.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:4000])
