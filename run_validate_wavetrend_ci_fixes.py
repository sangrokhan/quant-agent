import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = "strategies/2026-09-15_wavetrend_ci_sizing_sma_trend.py"
spec = importlib.util.spec_from_file_location("wt_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

configs = {
    "SPY": {"loader": load_equity, "params": {"trend_window": 100, "channel_length": 10, "average_length": 21,
                 "zscore_window": 100, "base_exposure": 0.4, "sensitivity": 0.6, "leverage_cap": 1.0, "deadband": 0.25}},
    "BTC/USDT": {"loader": load_crypto_daily, "params": {"trend_window": 40, "channel_length": 10, "average_length": 21,
                 "zscore_window": 100, "base_exposure": 0.15, "sensitivity": 0.6, "leverage_cap": 0.25, "deadband": 0.20}},
    "ETH/USDT": {"loader": load_crypto_daily, "params": {"trend_window": 40, "channel_length": 10, "average_length": 21,
                 "zscore_window": 100, "base_exposure": 0.15, "sensitivity": 0.6, "leverage_cap": 0.25, "deadband": 0.20}},
}

all_results = {}
for sym, cfg in configs.items():
    params = cfg["params"]
    loader = cfg["loader"]
    price_df = loader(sym, start, end)

    returns = strat.generate_returns(price_df, **params)
    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    signals = strat.generate_signals(price_df, **params)
    num_trades = int((signals.diff().fillna(0) != 0).sum())
    cost_pass, cost_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

    idx_df = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
    n_splits = 4
    slice_len = len(idx_df) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * slice_len
        e = (i + 1) * slice_len if i < n_splits - 1 else len(idx_df)
        slice_df = idx_df.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **params)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
             "n_splits": n_splits, "per_split_passed": wf_results,
             "note": "manual 4-equal-slice fallback"}

    param_grid_results = {}
    if sym == "SPY":
        sweep_vals = [(tw, db) for tw in [60, 100, 150] for db in [0.2, 0.25, 0.3, 0.35]]
        for tw, db in sweep_vals:
            p2 = dict(params); p2["trend_window"]=tw; p2["deadband"]=db
            r = strat.generate_returns(price_df, **p2)
            import vectorbt as vbt
            s = r.vbt.returns(freq="1D").sharpe_ratio()
            param_grid_results[f"tw{tw}_db{db}"] = float(s) if s is not None else 0.0
    else:
        sweep_vals = [(lc, be) for lc in [0.25, 0.3, 0.35] for be in [0.1, 0.15, 0.2]]
        for lc, be in sweep_vals:
            p2 = dict(params); p2["leverage_cap"]=lc; p2["base_exposure"]=be
            r = strat.generate_returns(price_df, **p2)
            import vectorbt as vbt
            s = r.vbt.returns(freq="1D").sharpe_ratio()
            param_grid_results[f"lc{lc}_be{be}"] = float(s) if s is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    all_results[sym] = {
        "params": params,
        "sharpe_ratio": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": cost_pass, **cost_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
    }

with open("validators_wavetrend_ci_fixes.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(json.dumps(all_results, indent=2, default=str))
