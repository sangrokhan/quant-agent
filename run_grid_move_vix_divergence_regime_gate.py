import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-24_move_vix_divergence_regime_gate.py"
spec = importlib.util.spec_from_file_location("strat_movevix", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "divergence_threshold": [0.5, 1.0, 1.5],
        "sma_window": [30, 50, 100],
    },
    symbols={"equity": ["QQQ", "SPY"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=gspec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open("grid_summary_move_vix_divergence_regime_gate.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

with open("grid_cells_move_vix_divergence_regime_gate.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
