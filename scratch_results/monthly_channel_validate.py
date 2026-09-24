import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-24_monthly_channel_3blackcandle_exit.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

import vectorbt as vbt  # noqa: F401,E402
from loaders import load_equity  # noqa: E402
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_walk_forward,
    check_parameter_sensitivity,
)  # noqa: E402

start = datetime(2016, 1, 1)
end = datetime(2026, 9, 1)

params = {"trend_sma_months": 30, "min_uptrend_months": 18}

results = {}
for symbol in ["QQQ", "SPY"]:
    df = load_equity(symbol, start, end)
    returns = strat.generate_returns(df, **params)

    sharpe_ok, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_ok, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)

    sig = strat.generate_signals(df, **params)
    n_trades = int((sig.diff().fillna(0) > 0).sum())

    tc_ok, tc_ev = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=max(n_trades, 1)
    )

    def strat_fn(price_slice):
        return strat.generate_returns(price_slice, **params)

    try:
        wf_ok, wf_ev = check_walk_forward(df, strat_fn, n_splits=4)
    except Exception as e:
        wf_ok, wf_ev = None, {"error": str(e)}

    results[symbol] = {
        "sharpe": sharpe_ev, "sharpe_passed": sharpe_ok,
        "mdd": mdd_ev, "mdd_passed": mdd_ok,
        "tc": tc_ev, "tc_passed": tc_ok,
        "walk_forward": wf_ev, "wf_passed": wf_ok,
        "n_trades_approx": n_trades,
    }

print(json.dumps(results, indent=2, default=str))
with open("scratch_results/monthly_channel_validate.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
