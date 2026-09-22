import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "strategies"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
from datetime import datetime
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", "strategies/2026-09-22_fisher_kst_dual_confirmation.py"
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec

gs = GridSpec(
    param_grid={"fisher_window": [10, 20], "trend_window": [0, 100]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gs,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
cells = [
    {
        "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
        "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "mdd": c.mdd,
        "passed": c.passed, "error": c.error,
    }
    for c in result.cells
]
with open("grid_cells_fisher_kst.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

summary = result.summary()
with open("grid_summary_fisher_kst.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))

from collections import defaultdict
agg = defaultdict(list)
for c in cells:
    if c["asset_class"] == "equity" and c["sharpe"] is not None:
        agg[(c["symbol"], str(c["params"]))].append(c["sharpe"])
for k, v in agg.items():
    print(k, "avg_sharpe_across_regimes=", sum(v) / len(v), v)
