import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-08_btc_gold_ratio_zscore_pairs.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

# Only crypto asset class makes sense here (BTC/USDT is price_df; GLD fetched
# internally). "equity" symbols would be nonsensical (price_df would be an
# equity series compared against itself as "gold").
gspec = GridSpec(
    param_grid={
        "window": [30, 60, 90],
        "entry_z": [1.5, 2.0, 2.5],
        "stop_z": [3.0, 3.5],
    },
    symbols={"crypto": ["BTC/USDT", "ETH/USDT"]},
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

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_btcgold.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
