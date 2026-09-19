import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "gsr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_gold_silver_ratio_rsi5_gld.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity

spec = GridSpec(
    param_grid={
        "rsi_period": [3, 5, 7],
        "rsi_entry": [70.0, 75.0, 80.0],
        "rsi_exit": [40.0, 50.0, 60.0],
    },
    symbols={"equity": ["GLD"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=spec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_summary_gold_silver_ratio_rsi5.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
