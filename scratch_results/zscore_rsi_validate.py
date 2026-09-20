import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-20_zscore_rsi_meanrev.py"
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
    params = {"entry_z": -1.5, "exit_z": 1.0, "max_hold_days": 10}
    r = strat.generate_returns(price_df, **params)
    pos = strat.generate_signals(price_df, **params)
    num_trades = int((pos.diff().abs() > 0).sum())

    sh_pass, sh_ev = check_sharpe_ratio(r)
    mdd_pass, mdd_ev = check_max_drawdown(r)
    tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=5.0, num_trades=num_trades)

    n_splits = 4
    idx = price_df.index
    chunk_bounds = [int(i * len(idx) / n_splits) for i in range(n_splits + 1)]
    wf_results = []
    for i in range(n_splits):
        lo, hi = chunk_bounds[i], chunk_bounds[i + 1]
        slice_df = price_df.iloc[lo:hi]
        if slice_df.empty:
            continue
        rr = strat.generate_returns(slice_df, **params)
        sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = wf_pass_fraction >= 0.75
    wf_ev = {
        "metric": "walk_forward_pass_fraction_manual",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
    }

    sweep = {}
    for ez in [-2.0, -1.5]:
        for xz in [0.5, 1.0]:
            for mh in [5, 10]:
                rr = strat.generate_returns(price_df, entry_z=ez, exit_z=xz, max_hold_days=mh)
                sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
                sweep[f"ez={ez},xz={xz},mh={mh}"] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(sweep)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sh_ev, "sharpe_pass": sh_pass,
        "mdd": mdd_ev, "mdd_pass": mdd_pass,
        "tc": tc_ev, "tc_pass": tc_pass,
        "wf": wf_ev, "wf_pass": wf_pass,
        "param_sensitivity": ps_ev, "param_sensitivity_pass": ps_pass,
    }

print(json.dumps(results, indent=2, default=str))
with open("scratch_results/validate_result_zscore_rsi.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
