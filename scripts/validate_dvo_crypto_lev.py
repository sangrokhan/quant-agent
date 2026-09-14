import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-14_dvo_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

BEST = dict(rank_lookback=126, base_exposure=0.24, sensitivity=0.12, trend_window=30, deadband=0.2, leverage_cap=0.3)

out_all = {}
for symbol in ["BTC/USDT", "ETH/USDT"]:
    df = load_crypto(symbol, datetime(2017,1,1), datetime(2026,9,1), interval="1d")
    returns = strat.generate_returns(df, **BEST)

    sharpe = check_sharpe_ratio(returns)
    mdd = check_max_drawdown(returns)
    sig = strat.generate_signals(df, **BEST)
    num_trades = int((sig.diff().abs() > 0).sum())
    tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    idx = df.index
    step = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * step
        e = len(idx) if i == n_splits - 1 else (i + 1) * step
        slice_df = df.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **BEST)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf = (bool(wf_pass_fraction >= 0.75), {
        "metric": "walk_forward_pass_fraction",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
    })

    param_grid_results = {}
    for lev in [0.27, 0.3, 0.33]:
        be, se = 0.8*lev, 0.4*lev
        r = strat.generate_returns(df, rank_lookback=126, base_exposure=be, sensitivity=se, trend_window=30, deadband=0.2, leverage_cap=lev)
        sh = check_sharpe_ratio(r)[1]["value"]
        param_grid_results[f"lev={lev}"] = sh if sh is not None else 0.0
    psens = check_parameter_sensitivity(param_grid_results)

    out_all[symbol] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "param_sensitivity": psens, "num_trades": num_trades}

print(json.dumps(out_all, indent=2, default=str))
with open("validators_dvo_crypto_lev.json", "w") as f:
    json.dump(out_all, f, indent=2, default=str)
