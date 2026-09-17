import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-17_adx_breakout_volume_calhoun.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

spec = GridSpec(
    param_grid={
        "trigger_level": [35.0, 40.0, 45.0],
        "exit_level": [20.0, 25.0],
        "volume_multiplier": [1.1, 1.3],
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
with open("grid_result_adx_breakout_volume.json","w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [dict(params=c.params, asset_class=c.asset_class, symbol=c.symbol, vol_regime=c.vol_regime_label, sharpe=c.sharpe, mdd=c.mdd, passed=c.passed, error=c.error) for c in result.cells]
with open("grid_cells_adx_breakout_volume.json","w") as f:
    json.dump(cells, f, indent=2, default=str)
