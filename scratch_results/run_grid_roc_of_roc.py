import sys, os, importlib.util, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "validation"))
sys.path.insert(0, os.path.join(ROOT, "data"))
os.chdir(ROOT)
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
from datetime import datetime

spec_path = "strategies/2026-09-28_roc_of_roc_thrust_agreement_trend.py"
spec = importlib.util.spec_from_file_location("rocroc_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "velocity_length": [5, 9, 14],
        "trend_window": [30, 50, 100],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("scratch_results/roc_of_roc_grid_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
