import importlib.util
import sys
from datetime import datetime
import itertools

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity  # noqa: E402
from validators import check_sharpe_ratio, check_max_drawdown  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-16_clenow_regression_momentum_sizing.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2015, 1, 1)
end = datetime(2026, 9, 1)
price_df = load_equity("QQQ", start, end)

best = None
results = []
for mom_window, rank_threshold, regime_window, stop_window, leverage_cap in itertools.product(
    [80, 90, 100, 110], [0.75, 0.78, 0.8, 0.82, 0.85], [180, 200, 220], [80, 100, 120], [1.0]
):
    try:
        r = strat.generate_returns(
            price_df,
            mom_window=mom_window,
            regime_window=regime_window,
            stop_window=stop_window,
            rank_threshold=rank_threshold,
            leverage_cap=leverage_cap,
        )
        sh_pass, sh_ev = check_sharpe_ratio(r)
        mdd_pass, mdd_ev = check_max_drawdown(r)
        sharpe = sh_ev.get("value")
        mdd = mdd_ev.get("value")
    except Exception:
        continue
    results.append((sharpe, mdd, mom_window, rank_threshold, regime_window, stop_window, leverage_cap))

results.sort(key=lambda x: (x[0] if x[0] is not None else -999), reverse=True)
for row in results[:15]:
    print(row)
