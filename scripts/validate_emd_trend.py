import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_ehlers_emd_trend_mode.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_parameter_sensitivity,
)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

configs = {
    "QQQ": dict(period=15, fraction=5.0, max_hold_days=40),
    "SPY": dict(period=30, fraction=3.0, max_hold_days=60),
}

results = {}
for sym, params in configs.items():
    price_df = load_equity(sym, start, end)
    r = strat.generate_returns(price_df, **params)
    sh_pass, sh_ev = check_sharpe_ratio(r)
    mdd_pass, mdd_ev = check_max_drawdown(r)

    position = strat.generate_signals(price_df, **params)
    num_trades = int((position.diff().abs() > 1e-9).sum())
    tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=5.0, num_trades=num_trades)

    param_grid_results = {}
    for f in [2.0, 3.0, 5.0, 8.0, 10.0]:
        p2 = dict(params)
        p2["fraction"] = f
        r2 = strat.generate_returns(price_df, **p2)
        sh2_pass, sh2_ev = check_sharpe_ratio(r2)
        param_grid_results[f"fraction={f}"] = sh2_ev.get("value")
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)

    results[sym] = {
        "params": params,
        "sharpe": sh_ev, "mdd": mdd_ev, "tc": tc_ev, "param_sensitivity": ps_ev,
        "num_trades": num_trades,
        "all_pass": bool(sh_pass and mdd_pass and tc_pass and ps_pass),
    }
    print(sym, "sharpe", sh_pass, "mdd", mdd_pass, "tc", tc_pass, "ps", ps_pass, "trades", num_trades)

with open("validate_result_emd_trend.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
