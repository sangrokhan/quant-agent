import sys, os, json, warnings
warnings.filterwarnings("ignore")
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, "strategies")
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-26_audjpy_carry_regime_trend_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "trend_window": [50, 100, 150],
        "carry_ma_window": [150, 200],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_audjpy_carry_regime.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))

from collections import defaultdict
agg = defaultdict(list)
for c in result.cells:
    key = (c.params.get("trend_window"), c.params.get("carry_ma_window"), c.asset_class, c.symbol)
    agg[key].append((c.vol_regime_label, c.sharpe, c.error))
for k in sorted(agg.keys()):
    print(k, agg[k])
