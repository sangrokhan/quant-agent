import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
from datetime import datetime
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-06_elder_safezone_ema_trend.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

params = dict(ema_span=20, safezone_factor=3.0)
out_all = {}
for symbol in ["SPY", "QQQ"]:
    df = load_equity(symbol, datetime(2018,1,1), datetime(2026,9,1))
    returns = strat.generate_returns(df, **params)

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)

    position = strat.generate_signals(df, **params)
    num_trades = int((position.diff() == 1).sum())
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

    import numpy as np, vectorbt as vbt
    n_splits = 4
    idx = df.index
    chunks = np.array_split(idx, n_splits)
    per_split = []
    for c in chunks:
        if len(c) == 0:
            continue
        slice_df = df.loc[c]
        r = strat.generate_returns(slice_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        per_split.append(bool(sh is not None and sh > 0))
    wf_pass_fraction = (sum(per_split) / len(per_split)) if per_split else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "n_splits": n_splits, "per_split_passed": per_split}

    grid_results = {}
    for es in [20, 50]:
        for sf in [2.0, 2.5, 3.0]:
            r = strat.generate_returns(df, ema_span=es, safezone_factor=sf)
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            grid_results[f"es={es},sf={sf}"] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(grid_results, max_relative_std=0.5)

    out = {
        "symbol": symbol,
        "num_trades": num_trades,
        "sharpe": sharpe_ev, "sharpe_pass": sharpe_pass,
        "mdd": mdd_ev, "mdd_pass": mdd_pass,
        "tc": tc_ev, "tc_pass": tc_pass,
        "walk_forward": wf_ev, "wf_pass": wf_pass,
        "param_sensitivity": ps_ev, "ps_pass": ps_pass,
        "grid_results": grid_results,
    }
    out_all[symbol] = out

print(json.dumps(out_all, indent=2, default=str))
with open("/tmp/safezone_validators.json", "w") as f:
    json.dump(out_all, f, default=str)
