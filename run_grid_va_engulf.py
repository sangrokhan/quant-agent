import sys, os, json
import importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
from datetime import datetime

spec = importlib.util.spec_from_file_location(
    "va_engulf_strat", os.path.join(os.path.dirname(__file__), "strategies", "2026-09-27_value_area_engulfing_reclaim.py")
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto

spec_g = GridSpec(
    param_grid={
        "lookback": [15, 20, 30],
        "vol_mult": [1.2, 1.5],
        "max_hold_days": [6, 10],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec_g,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_summary_value_area_engulfing_reclaim.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:3000])
