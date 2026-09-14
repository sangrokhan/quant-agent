import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-14_tmf_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("tmf_strat2", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

# Follow-up: crypto leverage_cap-restricted grid (using the same TMF sizing
# strategy file, no code change needed -- leverage_cap/base_exposure are
# already keyword params). Tests whether capping crypto leverage at 0.4-0.5
# (vs the 1.0 default used in the original grid) fixes crypto's MDD failure
# across all vol regimes, not just at the single best full-sample config.
gs = GridSpec(
    param_grid={
        "sensitivity": [0.3, 0.5, 0.7],
        "leverage_cap": [0.3, 0.4, 0.5],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

# base_exposure must track leverage_cap (half of cap, same ratio as the
# original strategy's default base_exposure=0.5/leverage_cap=1.0)
def _returns_fn(price_df, **p):
    lev = p.get("leverage_cap", 0.4)
    return strat.generate_returns(
        price_df,
        base_exposure=lev * 0.5,
        deadband=0.15,
        sensitivity=p.get("sensitivity", 0.5),
        leverage_cap=lev,
    )

result = run_strategy_grid(
    generate_returns_fn=_returns_fn,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto_daily},
    spec=gs,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_tmf_sizing_leverage_capped.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
