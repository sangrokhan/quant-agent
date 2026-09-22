import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-23_qld_regime_rotation_trailing_stop.py"
spec = importlib.util.spec_from_file_location("strat_qldts", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "stop_loss_pct": [0.04, 0.06, 0.08],
        "trend_sma": [150, 200],
    },
    symbols={"equity": ["QLD", "SSO"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2016, 6, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_summary_qld_regime_trailing_stop.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [{
    "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
    "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "sharpe_passed": c.sharpe_passed,
    "max_drawdown": getattr(c, "max_drawdown", None),
} for c in result.cells]
with open("grid_cells_qld_regime_trailing_stop.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
