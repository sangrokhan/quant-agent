import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "gold_btc_composite",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_gold_bitcoin_dual_momentum_composite.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)

spec = GridSpec(
    param_grid={
        "vol_cap": [0.15, 0.20, 0.25],
        "lookback_weeks_1": [4],
        "lookback_weeks_2": [8],
        "lookback_weeks_3": [12],
    },
    symbols={"equity": ["GLD", "SLV"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_summary_gold_bitcoin_dual_momentum_composite.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
