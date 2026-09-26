import sys, json
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("wk", "strategies/2026-09-26_weekly_inside_week_breakout.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2019,1,1), datetime(2026,9,1)
results = {}
params = dict(target_mult=1.5, max_hold_days=20)
for sym in ["QQQ", "SPY", "BTC/USDT", "ETH/USDT"]:
    if "/" in sym:
        df = load_crypto(sym, start=start, end=end)
    else:
        df = load_equity(sym, start=start, end=end)
    rets = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    num_trades = int((pos.diff().abs() == 1).sum())
    sharpe = check_sharpe_ratio(rets)
    mdd = check_max_drawdown(rets)
    tc = check_transaction_cost_survival(rets, cost_bps_per_trade=10.0, num_trades=num_trades)
    results[sym] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "num_trades": num_trades}

# parameter sensitivity on QQQ across target_mult
param_results = {}
for tm in [1.5, 2.0, 3.0]:
    df = load_equity("QQQ", start=start, end=end)
    p2 = dict(params); p2["target_mult"] = tm
    rets = strat.generate_returns(df, **p2)
    sh = check_sharpe_ratio(rets)
    param_results[str(tm)] = sh[1]["value"]
ps = check_parameter_sensitivity(param_results)
results["QQQ_param_sensitivity"] = ps

print(json.dumps(results, indent=2, default=str))
with open("validate_result_weekly_inside_week_breakout.json","w") as f:
    json.dump(results, f, indent=2, default=str)
