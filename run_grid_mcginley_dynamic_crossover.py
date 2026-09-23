import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-24_mcginley_dynamic_crossover.py"
spec = importlib.util.spec_from_file_location("strat_md", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "md_period": [14, 20, 30],
        "rsi_threshold": [45, 50, 55],
        "max_hold_days": [15, 20],
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
with open("grid_summary_mcginley_dynamic_crossover.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))

cells = [
    {
        "params": c.params,
        "asset_class": c.asset_class,
        "symbol": c.symbol,
        "vol_regime": c.vol_regime_label,
        "sharpe": c.sharpe,
        "passed": c.passed,
    }
    for c in result.cells
]
with open("grid_cells_mcginley_dynamic_crossover.json", "w") as f:
    json.dump(cells, f, default=str)
