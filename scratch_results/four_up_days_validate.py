import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_four_up_days_hold_to_friday.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

import vectorbt as vbt  # noqa: F401,E402
from loaders import load_equity  # noqa: E402
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_parameter_sensitivity,
)  # noqa: E402

start = datetime(2016, 1, 1)
end = datetime(2026, 9, 1)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    params = {"streak_len": 4}
    r = strat.generate_returns(price_df, **params)
    pos = strat.generate_signals(price_df, **params)
    num_trades = int((pos.diff().abs() > 0).sum())

    sh_pass, sh_ev = check_sharpe_ratio(r)
    mdd_pass, mdd_ev = check_max_drawdown(r)
    tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=5.0, num_trades=num_trades)

    sweep = {}
    for sl in [3, 4, 5]:
        rr = strat.generate_returns(price_df, streak_len=sl)
        sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
        sweep[f"streak_len={sl}"] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(sweep)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sh_ev, "sharpe_pass": sh_pass,
        "mdd": mdd_ev, "mdd_pass": mdd_pass,
        "tc": tc_ev, "tc_pass": tc_pass,
        "param_sensitivity": ps_ev, "param_sensitivity_pass": ps_pass,
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_four_up_days_hold_to_friday.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
