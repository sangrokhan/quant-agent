import sys, os, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
sys.path.insert(0, "strategies")
from loaders import load_equity, load_crypto  # noqa: E402
from grid_test import run_strategy_grid, GridSpec  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-27_broadening_top_bottom_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "touch_tolerance": [0.01, 0.015, 0.02],
        "min_touches": [3, 4],
        "max_hold_days": [15, 25],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_summary_broadening_top_bottom.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:3000])
