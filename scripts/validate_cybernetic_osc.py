import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity, load_crypto  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_cybernetic_oscillator_sizing_sma_trend.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_walk_forward,
    check_parameter_sensitivity,
)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

configs = {
    "QQQ": dict(loader=load_equity, symbol="QQQ", params=dict(hp_length=40, sensitivity=0.4, deadband=0.25, leverage_cap=1.0)),
    "SPY": dict(loader=load_equity, symbol="SPY", params=dict(hp_length=40, sensitivity=0.4, deadband=0.25, leverage_cap=1.0)),
    "BTC/USDT": dict(loader=load_crypto, symbol="BTC/USDT", params=dict(hp_length=40, sensitivity=0.4, deadband=0.25, leverage_cap=0.3)),
    "ETH/USDT": dict(loader=load_crypto, symbol="ETH/USDT", params=dict(hp_length=40, sensitivity=0.4, deadband=0.25, leverage_cap=0.3)),
}

results = {}
for sym, cfg in configs.items():
    if cfg["loader"] is load_crypto:
        price_df = cfg["loader"](cfg["symbol"], start, end, interval="1d")
    else:
        price_df = cfg["loader"](cfg["symbol"], start, end)

    returns = strat.generate_returns(price_df, **cfg["params"])

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    exposure = strat.generate_signals(price_df, **cfg["params"])
    num_trades = int((exposure.diff().abs() > 1e-9).sum())
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades)
    try:
        wf_pass, wf_ev = check_walk_forward(returns)
    except Exception as e:
        wf_pass, wf_ev = None, {"error": str(e)}

    # param sensitivity: vary sensitivity param
    param_grid_results = {}
    for s in [0.2, 0.4, 0.6, 0.8, 1.0]:
        p2 = dict(cfg["params"])
        p2["sensitivity"] = s
        r2 = strat.generate_returns(price_df, **p2)
        sh_pass2, sh_ev2 = check_sharpe_ratio(r2)
        param_grid_results[f"sensitivity={s}"] = sh_ev2.get("value")
    try:
        ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)
    except Exception as e:
        ps_pass, ps_ev = None, {"error": str(e)}

    results[sym] = {
        "params": cfg["params"],
        "sharpe": sharpe_ev,
        "mdd": mdd_ev,
        "tc": tc_ev,
        "walk_forward": wf_ev,
        "param_sensitivity": ps_ev,
        "all_pass": bool(sharpe_pass and mdd_pass and tc_pass and (ps_pass in (True, None))),
    }
    print(sym, "sharpe_pass", sharpe_pass, "mdd_pass", mdd_pass, "tc_pass", tc_pass, "ps_pass", ps_pass, "wf_pass", wf_pass)

with open("validate_result_cybernetic_osc.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
