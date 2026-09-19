import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import numpy as np
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-20_force_index_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

START = datetime(2019, 1, 1)
END = datetime(2026, 9, 1)

CONFIGS = {
    "equity:QQQ": (load_equity, "QQQ", dict(sensitivity=0.4, deadband=0.25)),
    "equity:SPY": (load_equity, "SPY", dict(sensitivity=0.4, deadband=0.25)),
    "crypto:BTC/USDT": (load_crypto, "BTC/USDT", dict(sensitivity=0.4, deadband=0.15, leverage_cap=0.3)),
    "crypto:ETH/USDT": (load_crypto, "ETH/USDT", dict(sensitivity=0.4, deadband=0.15, leverage_cap=0.3)),
}

def manual_walk_forward(price_df, params, n_splits=4, min_pass_fraction=0.75):
    df = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
    n = len(df)
    chunk = n // n_splits
    results = []
    for i in range(n_splits):
        s = i * chunk
        e = n if i == n_splits - 1 else (i + 1) * chunk
        slice_df = df.iloc[s:e]
        if slice_df.empty:
            continue
        returns = strat.generate_returns(slice_df, **params)
        try:
            import vectorbt as vbt
            sharpe = returns.vbt.returns(freq="D").sharpe_ratio() if len(returns) else None
        except Exception:
            sharpe = None
        results.append(bool(sharpe is not None and sharpe > 0))
    pass_fraction = (sum(results) / len(results)) if results else 0.0
    passed = bool(pass_fraction >= min_pass_fraction)
    return passed, {"metric": "walk_forward_pass_fraction", "value": pass_fraction,
                     "threshold": min_pass_fraction, "n_splits": n_splits, "per_split_passed": results,
                     "note": "manual contiguous 4-split (vectorbt.utils.splitting.RangeSplitter unavailable in installed vbt 1.1.0)"}

all_results = {}
for key, (loader, symbol, params) in CONFIGS.items():
    try:
        price_df = loader(symbol, START, END, interval="1d")
    except TypeError:
        price_df = loader(symbol, START, END)

    returns = strat.generate_returns(price_df, **params)
    exposure = strat.generate_signals(price_df, **params)
    num_trades = int((exposure.diff().abs() > 0).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    wf_pass, wf_ev = manual_walk_forward(price_df, params)

    cells = json.load(open("grid_cells_force_index_sizing.json"))
    pg = {}
    for c in cells:
        if c["symbol"] == symbol and c["vol_regime_label"] == "low":
            k = f"sens={c['params']['sensitivity']},db={c['params']['deadband']}"
            if c["sharpe"] is not None:
                pg[k] = c["sharpe"]
    ps_pass, ps_ev = check_parameter_sensitivity(pg) if pg else (None, {})

    all_results[key] = {
        "params": params,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "tc_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "param_sensitivity": {"passed": ps_pass, **ps_ev},
        "num_trades": num_trades,
        "all_pass": bool(sharpe_pass and mdd_pass and tc_pass and wf_pass and (ps_pass is not False)),
    }

print(json.dumps(all_results, indent=2, default=str))
with open("validate_result_force_index_sizing_final.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
