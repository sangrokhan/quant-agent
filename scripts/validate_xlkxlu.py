import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-17_xlk_xlu_ratio_regime.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

BEST = dict(ma_window=100)

xlkxlu_grid = json.load(open("/tmp/xlkxlu_grid_result.json"))

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start=datetime(2019,1,1), end=datetime(2026,9,1))
    returns = strat.generate_returns(price_df, **BEST)
    signals = strat.generate_signals(price_df, **BEST)
    num_trades = int((signals.diff().fillna(0).abs() > 0).sum())

    out = {}
    out["sharpe_ratio"] = check_sharpe_ratio(returns)
    out["max_drawdown"] = check_max_drawdown(returns)
    out["transaction_cost_survival"] = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10, num_trades=num_trades)
    try:
        out["walk_forward"] = check_walk_forward(
            price_df, lambda df: strat.generate_returns(df, **BEST))
    except Exception as e:
        out["walk_forward"] = (False, {"error": str(e)})

    param_grid_results = {}
    for c in xlkxlu_grid["cells"]:
        if c["symbol"] == symbol and c["sharpe"] is not None:
            key = json.dumps(c["params"], sort_keys=True)
            param_grid_results[key] = c["sharpe"]
    try:
        out["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)
    except Exception as e:
        out["parameter_sensitivity"] = (False, {"error": str(e)})

    results[symbol] = {k: (v[0], v[1]) for k, v in out.items()}
    print(symbol, {k: v[0] for k, v in out.items()})

with open("/tmp/xlkxlu_validators.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
