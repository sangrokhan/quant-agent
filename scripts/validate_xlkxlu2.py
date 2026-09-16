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
    check_parameter_sensitivity,
)

params = dict(ma_window=100)

xlkxlu_grid = json.load(open("/tmp/xlkxlu_grid_result.json"))

results = {}
for symbol in ["QQQ", "SPY"]:
    df = load_equity(symbol, datetime(2019,1,1), datetime(2026,9,1))
    returns = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    num_trades = int((pos.diff().abs() > 1e-9).sum())
    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    split_size = len(df) // n_splits
    wf_results = []
    for s in range(n_splits):
        lo = s * split_size
        hi = len(df) if s == n_splits - 1 else (s + 1) * split_size
        slice_df = df.iloc[lo:hi]
        if len(slice_df) < 60:
            continue
        r = strat.generate_returns(slice_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = wf_pass_fraction >= 0.75

    param_grid_results = {}
    for c in xlkxlu_grid["cells"]:
        if c["symbol"] == symbol and c["sharpe"] is not None:
            key = json.dumps(c["params"], sort_keys=True)
            param_grid_results[key] = c["sharpe"]
    psens_pass, psens_ev = check_parameter_sensitivity(param_grid_results)

    results[symbol] = {
        "sharpe_ratio": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": tc_pass, **tc_ev, "num_trades": num_trades},
        "walk_forward": {"passed": wf_pass, "value": wf_pass_fraction, "per_split": wf_results, "note": "manual 4-split fallback (vectorbt RangeSplitter broken)"},
        "parameter_sensitivity": {"passed": psens_pass, **psens_ev},
    }
    print(symbol, {k: v["passed"] for k, v in results[symbol].items()})

with open("/tmp/xlkxlu_validators2.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
