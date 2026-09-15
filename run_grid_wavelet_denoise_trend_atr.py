import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from functools import partial
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))
from grid_test import run_strategy_grid, GridSpec

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = "strategies/2026-09-16_wavelet_denoise_trend_atr.py"
mspec = importlib.util.spec_from_file_location("wavelet_strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

grid_spec = GridSpec(
    param_grid={
        "wavelet_window": [45, 60, 75],
        "atr_mult": [0.0, 0.25],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto_daily},
    spec=grid_spec,
    start=start,
    end=end,
)

summary = result.summary()
with open("grid_result_wavelet_denoise_trend_atr.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

with open("grid_cells_wavelet_denoise_trend_atr.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
