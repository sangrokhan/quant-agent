import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-08_ethbtc_breakout_stability_gate.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "breakout_window": [10, 20, 40],
        "btc_stability_ratio": [0.85, 1.0, 1.2],
        "max_hold_days": [15, 20],
    },
    symbols={"crypto": ["ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"crypto": load_crypto},
    spec=gspec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_ethbtc_breakout.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
