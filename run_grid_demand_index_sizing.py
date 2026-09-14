import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-14_demand_index_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("di_strat_grid", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

# Per this cron trigger's own leverage-cap finding (2026-09-14-124/125):
# apply asset-class-appropriate leverage from the start rather than
# defaulting to 1.0x uniformly. Since GridSpec applies the same param_grid
# to both asset classes, run two separate grids and merge results.
gs_equity = GridSpec(
    param_grid={"sensitivity": [0.3, 0.5, 0.7], "deadband": [0.10, 0.15]},
    symbols={"equity": ["QQQ", "SPY"]},
    vol_regime_splits=3,
)
gs_crypto = GridSpec(
    param_grid={"sensitivity": [0.3, 0.5, 0.7], "leverage_cap": [0.3, 0.4]},
    symbols={"crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)


def _crypto_returns_fn(price_df, **p):
    lev = p.get("leverage_cap", 0.4)
    return strat.generate_returns(
        price_df, base_exposure=lev * 0.5, deadband=0.15,
        sensitivity=p.get("sensitivity", 0.5), leverage_cap=lev,
    )


result_eq = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=gs_equity,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)
result_cr = run_strategy_grid(
    generate_returns_fn=_crypto_returns_fn,
    loader_fn_by_asset_class={"crypto": load_crypto_daily},
    spec=gs_crypto,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary_eq = result_eq.summary()
summary_cr = result_cr.summary()
merged = {
    "equity_grid": summary_eq,
    "crypto_grid": summary_cr,
    "combined_pass_fraction": (summary_eq["passed_cells"] + summary_cr["passed_cells"]) / (summary_eq["total_cells"] + summary_cr["total_cells"]),
}
with open("grid_result_demand_index_sizing.json", "w") as f:
    json.dump(merged, f, indent=2, default=str)
print(json.dumps(merged, indent=2, default=str))
