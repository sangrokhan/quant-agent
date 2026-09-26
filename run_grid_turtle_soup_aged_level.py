import sys, os, json
sys.path.insert(0, os.path.join("data"))
sys.path.insert(0, os.path.join("validation"))
sys.path.insert(0, os.path.join("strategies"))
from datetime import datetime
from loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "turtle_soup_aged_level_fade",
    os.path.join("strategies", "2026-09-26_turtle_soup_aged_level_fade.py"),
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)
from grid_test import run_strategy_grid, GridSpec

spec = GridSpec(
    param_grid={
        "breakout_window": [10, 20, 30],
        "min_level_age": [2, 4, 8],
        "max_hold_days": [2, 3, 5],
    },
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
with open("grid_result_turtle_soup_aged_level.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, default=str)
with open("grid_summary_turtle_soup_aged_level.json", "w") as f:
    json.dump(summary, f, default=str)
