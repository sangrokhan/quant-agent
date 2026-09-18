import importlib.util
import sys
from datetime import datetime
import itertools

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity  # noqa: E402
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-14_kst_sizing_sma_trend.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2015, 1, 1)
end = datetime(2026, 9, 1)
price_df = load_equity("SPY", start, end)

results = []
for trend_window, zscore_window, sensitivity, deadband in itertools.product(
    [30, 40, 50, 60], [60, 90, 120, 150], [0.3, 0.4, 0.5, 0.6], [0.15, 0.20, 0.25, 0.30]
):
    r = strat.generate_returns(
        price_df,
        trend_window=trend_window,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        deadband=deadband,
    )
    sh_pass, sh_ev = check_sharpe_ratio(r)
    mdd_pass, mdd_ev = check_max_drawdown(r)
    sharpe = sh_ev.get("value")
    mdd = mdd_ev.get("value")
    if sharpe is not None and sharpe >= 1.0 and mdd is not None and mdd <= 0.25:
        exposure = strat.generate_signals(price_df, trend_window=trend_window, zscore_window=zscore_window, sensitivity=sensitivity, deadband=deadband)
        num_trades = int((exposure.diff().abs() > 1e-9).sum())
        tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=5.0, num_trades=num_trades)
        results.append((sharpe, mdd, tc_ev.get("value"), tc_pass, trend_window, zscore_window, sensitivity, deadband, num_trades))

results.sort(key=lambda x: x[0], reverse=True)
for row in results[:20]:
    print(row)
print("total passing sharpe+mdd:", len(results))
