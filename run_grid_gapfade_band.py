import sys, os, json
from datetime import datetime
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location(
    "gapfade_strat", "strategies/2026-09-28_gap_down_fade_midsize_band.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto

grid_spec = GridSpec(
    param_grid={
        "gap_min_threshold": [0.01, 0.015],
        "gap_max_threshold": [0.03, 0.05],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("/tmp/gapfade_grid_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
