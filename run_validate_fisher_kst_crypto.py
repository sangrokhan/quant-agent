import sys, os, json
from datetime import datetime
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from data.loaders import load_crypto
import importlib.util

spec = importlib.util.spec_from_file_location(
    "strat_fk", "strategies/2026-09-22_fisher_kst_dual_confirmation.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(fisher_window=20, trend_window=0)

all_cells = json.load(open("grid_cells_fisher_kst.json"))

for symbol in ["BTC/USDT", "ETH/USDT"]:
    df = load_crypto(symbol, datetime(2018, 1, 1), datetime(2026, 9, 1), interval="1d")
    returns = strat.generate_returns(df, **params)
    n_trades = int((strat.generate_signals(df, **params).diff().abs() > 0).sum())
    print(symbol, "n position changes:", n_trades, "nonzero ret days:", int((returns != 0).sum()), "of", len(returns))

    results = {}
    results["sharpe_ratio"] = check_sharpe_ratio(returns)
    results["max_drawdown"] = check_max_drawdown(returns)
    results["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=n_trades)

    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df
    n_splits = 4
    chunks = np.array_split(df_idx.index, n_splits)
    wf_results = []
    for chunk in chunks:
        if len(chunk) == 0:
            continue
        slice_df = df_idx.loc[chunk]
        r = strat.generate_returns(slice_df.reset_index(), **params)
        sharpe = None
        if len(r):
            import vectorbt as vbt
            sharpe = r.vbt.returns(freq="D").sharpe_ratio()
        wf_results.append(bool(sharpe is not None and sharpe > 0))
    wf_pass_fraction = sum(wf_results) / len(wf_results) if wf_results else 0.0
    results["walk_forward"] = (wf_pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
    })

    sym_cells = [c for c in all_cells if c["symbol"] == symbol and c["vol_regime"] == "mid" and c["sharpe"] is not None]
    param_grid_results = {str(c["params"]): c["sharpe"] for c in sym_cells}
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)

    out = {}
    for k, (p, e) in results.items():
        print(" ", k, "PASS" if p else "FAIL", e)
        out[k] = {"passed": p, **e}
    json.dump(out, open(f"validators_fisher_kst_{symbol.split('/')[0].lower()}.json", "w"), default=str)
