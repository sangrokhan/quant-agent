import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-10_aroon_chandelier_combo.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

spec = GridSpec(
    param_grid={
        "aroon_window": [14, 25],
        "chandelier_atr_mult": [2.5, 3.0, 3.5],
        "max_hold_days": [20, 40],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019,1,1), end=datetime(2026,9,1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_result_aroon_chandelier.json","w") as f:
    json.dump(summary, f, indent=2, default=str)
cells = [dict(params=c.params, asset_class=c.asset_class, symbol=c.symbol, vol_regime=c.vol_regime_label, sharpe=c.sharpe, mdd=c.mdd, passed=c.passed, error=c.error) for c in result.cells]
with open("grid_cells_aroon_chandelier.json","w") as f:
    json.dump(cells, f, indent=2, default=str)
