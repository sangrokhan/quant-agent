import sys, importlib.util, json
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from datetime import datetime
from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec

spec = importlib.util.spec_from_file_location(
    "odl", "strategies/2026-09-20_oneday_loss_magnitude_reversal.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "loss_threshold_pct": [-0.03, -0.05, -0.08],
        "require_high_volume": [True, False],
        "max_hold_days": [3, 5],
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
print(json.dumps(summary, indent=2, default=str))
with open("grid_result_oneday_loss_reversal.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
