import sys, os, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
sys.path.insert(0, "strategies")
from loaders import load_equity, load_crypto  # noqa: E402
from grid_test import run_strategy_grid, GridSpec  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-27_silj_sil_ratio_regime_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "trend_sma_window": [150, 200, 250],
        "ratio_sma_window": [50, 100, 150],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2016, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_summary_silj_sil.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
with open("grid_cells_silj_sil.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
