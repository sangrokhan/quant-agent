import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-24_demarker_midline_crossover.py"
spec = importlib.util.spec_from_file_location("strat_demmid", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "dem_window": [10, 14, 21],
        "trend_window": [50, 100],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_summary_demarker_midline_crossover.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))

from collections import defaultdict
agg = defaultdict(lambda: [0, 0])
for c in result.cells:
    key = (c.symbol, c.params['dem_window'], c.params['trend_window'])
    agg[key][1] += 1
    if c.passed:
        agg[key][0] += 1
print("--- configs ---")
for k, v in sorted(agg.items(), key=lambda x: -x[1][0] / x[1][1]):
    print(k, v, round(v[0] / v[1], 2))

with open("grid_cells_demarker_midline_crossover.json", "w") as f:
    json.dump([
        {"symbol": c.symbol, "params": c.params,
         "passed": c.passed, "sharpe": getattr(c, "sharpe", None)}
        for c in result.cells
    ], f, indent=2, default=str)
