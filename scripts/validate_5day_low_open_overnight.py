import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util
import functools

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-17_5day_low_open_overnight_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

params = dict(n_days=10)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start=datetime(2019, 1, 1), end=datetime(2026, 9, 1))
    returns = strat.generate_returns(price_df, **params)
    position = strat.generate_signals(price_df, **params)
    num_trades = int((position.diff().fillna(0) != 0).sum() / 2)
    sharpe = check_sharpe_ratio(returns)
    mdd = check_max_drawdown(returns)
    tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    strat_fn = functools.partial(strat.generate_returns, **params)
    try:
        wf = check_walk_forward(price_df, strat_fn)
    except Exception as e:
        wf = (None, {"error": str(e)})
    results[symbol] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "num_trades": num_trades}

param_grid_results = {}
price_df_qqq = load_equity("QQQ", start=datetime(2019, 1, 1), end=datetime(2026, 9, 1))
for nd in [3, 5, 10]:
    p2 = dict(n_days=nd)
    r = strat.generate_returns(price_df_qqq, **p2)
    import vectorbt as vbt
    sharpe_val = r.vbt.returns(freq="D").sharpe_ratio()
    param_grid_results[str(nd)] = sharpe_val

ps = check_parameter_sensitivity(param_grid_results)

out = {
    "results": {k: {kk: (vv if kk == "num_trades" else (vv[0], vv[1])) for kk, vv in v.items()} for k, v in results.items()},
    "param_grid_results": param_grid_results,
    "param_sensitivity": ps,
}
print(json.dumps(out, indent=2, default=str))
with open("/tmp/5day_low_open_overnight_validators.json", "w") as f:
    json.dump(out, f, default=str)
