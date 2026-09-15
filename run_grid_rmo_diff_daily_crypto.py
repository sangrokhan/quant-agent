import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-15_rmo_diff_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("rmo_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gs = GridSpec(
    param_grid={
        "st2_span": [20, 30],
        "st3_span": [20, 30],
        "sensitivity": [0.4, 0.6, 0.8],
        "deadband": [0.20, 0.35],
    },
    symbols={"crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"crypto": load_crypto_daily},
    spec=gs,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_rmo_diff_daily_crypto.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:4000])

with open("grid_cells_rmo_diff_daily_crypto.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
