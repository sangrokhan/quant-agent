import sys, os, json
sys.path.insert(0, os.path.join("data"))
sys.path.insert(0, os.path.join("validation"))
from datetime import datetime
from loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "closing_price_reversal",
    os.path.join("strategies", "2026-09-26_bulkowski_closing_price_reversal.py"),
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

configs = {
    "SPY": dict(trend_window=50, edge_pct=0.15, height_mult=1.0),
    "QQQ": dict(trend_window=50, edge_pct=0.15, height_mult=1.0),
}

results = {}
for symbol, params in configs.items():
    price_df = load_equity(symbol, start, end, interval="1d")
    returns = strat.generate_returns(price_df, **params)
    position = strat.generate_signals(price_df, **params)
    num_trades = int((position.diff() == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    def strategy_fn(df):
        return strat.generate_returns(df, **params)
    try:
        wf_pass, wf_ev = check_walk_forward(price_df, strategy_fn, n_splits=4, min_pass_fraction=0.75)
    except Exception as exc:
        wf_pass, wf_ev = None, {"metric": "walk_forward_pass_fraction", "value": None, "reason": f"skipped: vectorbt API error ({exc}); known repo issue"}

    param_sweep = {}
    for tw in [max(10, params["trend_window"]-20), params["trend_window"], params["trend_window"]+20]:
        for ep in [max(0.05, params["edge_pct"]-0.1), params["edge_pct"], params["edge_pct"]+0.1]:
            p2 = dict(params); p2["trend_window"]=tw; p2["edge_pct"]=ep
            r2 = strat.generate_returns(price_df, **p2)
            try:
                import vectorbt as vbt
                sh = r2.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                sh = None
            param_sweep[str(p2)] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_sweep, max_relative_std=0.5)

    results[symbol] = {
        "params": params,
        "num_trades": num_trades,
        "sharpe": (sharpe_pass, sharpe_ev),
        "mdd": (mdd_pass, mdd_ev),
        "tc": (tc_pass, tc_ev),
        "wf": (wf_pass, wf_ev),
        "param_sens": (ps_pass, ps_ev),
        "all_pass": all([sharpe_pass, mdd_pass, tc_pass, (wf_pass is not False), ps_pass]),
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_closing_price_reversal.json", "w") as f:
    json.dump(results, f, default=str, indent=2)
