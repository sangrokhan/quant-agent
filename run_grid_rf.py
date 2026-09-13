import sys, os, json, time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

# load_crypto defaults to 1h bars (ccxt) -- for this compute-heavy rolling-
# retrain strategy, force daily bars for crypto too (matches equity
# granularity and keeps the retrain loop's row count in the same ballpark
# as equity, avoiding a ~24x blowup in wall-clock time).
load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-13_random_forest_direction_classifier.py")
spec = importlib.util.spec_from_file_location("rf_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

# Compute-heavy strategy (rolling retrain) -- keep grid small: 2 params x 2
# values each x 1 symbol per asset class (workload scoped down given ~20s
# per single-symbol run observed in timing test).
gs = GridSpec(
    param_grid={
        "retrain_period": [63, 126],
        "max_depth": [3, 5],
    },
    symbols={"equity": ["QQQ"], "crypto": ["BTC/USDT"]},
    vol_regime_splits=3,
)

t0 = time.time()
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto_daily},
    spec=gs,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
print("grid elapsed", time.time() - t0)

summary = result.summary()
with open("grid_result_rf.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
