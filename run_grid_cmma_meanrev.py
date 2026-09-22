import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "cmma_meanrev",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_cmma_meanrev.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)

spec = GridSpec(
    param_grid={
        "k": [10, 20, 30],
        "entry_threshold": [-0.5, -0.75],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_summary_cmma_meanrev.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
