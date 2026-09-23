import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-23_funding_rate_price_divergence_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity

START = datetime(2020, 1, 1)
END = datetime(2026, 9, 1)

# Best cells from grid: BTC 20/14/30 (sharpe 0.712, mdd 0.511), ETH 10/14/30 (sharpe 0.844, mdd 0.745)
configs = {
    "BTC/USDT": dict(symbol="BTC/USDT", divergence_window=20, funding_window=14, max_hold_days=30),
    "ETH/USDT": dict(symbol="ETH/USDT", divergence_window=10, funding_window=14, max_hold_days=30),
}

results = {}
for sym, params in configs.items():
    price_df = load_crypto(sym, START, END, interval="1d")
    returns = strat.generate_returns(price_df, **params)
    sh_pass, sh_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns)
    wf_pass, wf_ev = check_walk_forward(strat.generate_returns, price_df, params, n_splits=4)
    results[sym] = {
        "params": params,
        "sharpe_ratio": {"passed": sh_pass, "value": sh_ev["value"], "threshold": sh_ev.get("threshold")},
        "max_drawdown": {"passed": mdd_pass, "value": mdd_ev["value"], "threshold": mdd_ev.get("threshold")},
        "transaction_cost_survival": {"passed": tc_pass, "value": tc_ev["value"], "threshold": tc_ev.get("threshold")},
        "walk_forward": {"passed": wf_pass, "value": wf_ev["value"], "threshold": wf_ev.get("threshold")},
    }
    print(sym, results[sym])

with open("validate_result_funding_price_divergence.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
