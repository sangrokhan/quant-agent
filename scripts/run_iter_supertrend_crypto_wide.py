import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-03_supertrend_atr_longonly.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

# Crypto-tuned wider-band grid, per SERP guidance (Quantzee/TrendSpider):
# widen ATR multiplier to 3.5-5.0 and lengthen ATR period to 14-21 to filter
# out Bitcoin's sharp wick-driven whipsaws that killed the standard 10/3.0
# config decisively (0/54 crypto grid cells in 2026-09-04-053).
gspec = GridSpec(
    param_grid={
        "atr_period": [14, 21],
        "multiplier": [3.5, 4.0, 5.0],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_supertrend_crypto_wide.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
