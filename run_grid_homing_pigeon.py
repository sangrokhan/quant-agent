import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-21_homing_pigeon_volume_confirmed.py"
spec = importlib.util.spec_from_file_location("strat_hp", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

price_df = load_equity("QQQ", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
pos = strat.generate_signals(price_df)
print("trades (QQQ default):", int((pos.diff().abs() == 1).sum()), "total bars in position:", int(pos.sum()))

gspec = GridSpec(
    param_grid={
        "trend_lookback": [5, 10, 15],
        "vol_mult": [1.1, 1.3, 1.6],
        "exit_sma_window": [10, 20],
        "max_hold_days": [5, 10],
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
with open("grid_summary_homing_pigeon_volume_confirmed.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [{
    "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
    "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "sharpe_passed": c.sharpe_passed,
    "mdd": c.mdd, "mdd_passed": c.mdd_passed, "error": c.error,
} for c in result.cells]
with open("grid_cells_homing_pigeon_volume_confirmed.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
