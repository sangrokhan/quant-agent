import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-14_bop_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("bop_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gs = GridSpec(
    param_grid={
        "bop_sensitivity": [0.4, 0.6, 0.8],
        "deadband": [0.05, 0.10],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto_daily},
    spec=gs,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_bop_sizing.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))

import collections
by_sym = collections.defaultdict(list)
for c in result.cells:
    by_sym[c.symbol].append(c)
for sym, cells in by_sym.items():
    best = max(cells, key=lambda c: (c.sharpe if c.sharpe is not None else -999))
    passed = sum(1 for c in cells if c.passed)
    print(sym, "pass", passed, "/", len(cells), "best", best.params, "sharpe", best.sharpe, "regime", best.vol_regime_label)
