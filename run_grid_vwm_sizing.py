import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-15_vwm_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("vwm_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gs = GridSpec(
    param_grid={
        "mom_period": [10, 14],
        "smooth_period": [14, 20],
        "sensitivity": [0.5, 0.7],
        "deadband": [0.20, 0.30],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto_daily},
    spec=gs,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_vwm_sizing.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:4000])

# dump best cells per symbol for validator stage
with open("grid_cells_vwm_sizing.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
