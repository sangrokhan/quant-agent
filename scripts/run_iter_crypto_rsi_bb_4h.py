import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-08_crypto_4h_rsi_bb_meanrev_volspike.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

# Windows scaled x4 to approximate the source's 4h-chart recommendation
# using this repo's 1h crypto bars (bb_window=20 4h-bars ~ 80 1h-bars, etc).
gspec = GridSpec(
    param_grid={
        "bb_window": [60, 80],
        "rsi_oversold": [20, 25],
        "vol_spike_ratio": [1.5, 2.0],
    },
    symbols={"crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"crypto": load_crypto},
    spec=gspec,
    start=datetime(2020, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_crypto_rsi_bb_4h.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
