import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-24_ulcer_index_regime_gate.py"
spec = importlib.util.spec_from_file_location("strat_ui", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "ui_window": [10, 14, 20],
        "ui_gate_percentile": [0.4, 0.5, 0.6],
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
with open("grid_summary_ulcer_index_regime_gate.json", "w") as f:
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
with open("grid_cells_ulcer_index_regime_gate.json", "w") as f:
    json.dump(cells, f, default=str)
