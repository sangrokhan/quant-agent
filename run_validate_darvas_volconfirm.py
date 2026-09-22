import sys, os, json
from datetime import datetime
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from data.loaders import load_equity, load_crypto
import importlib.util

spec = importlib.util.spec_from_file_location(
    "strat_darvasv", "strategies/2026-09-23_darvas_box_volconfirm_trend_trail.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(high_lookback=30, confirm_days=5, volume_mult=1.2, sma_window=50)

cells = json.load(open("grid_cells_darvas_volconfirm_trend_trail.json"))

all_results = {}
for asset_class, symbol, loader in [
    ("equity", "QQQ", load_equity),
    ("equity", "SPY", load_equity),
    ("crypto", "BTC/USDT", load_crypto),
]:
    df = loader(symbol, datetime(2018, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **params)
    n_trades = int((strat.generate_signals(df, **params).diff().abs() > 0).sum())

    results = {}
    results["sharpe_ratio"] = check_sharpe_ratio(returns)
    results["max_drawdown"] = check_max_drawdown(returns)
    results["transaction_cost_survival"] = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=n_trades
    )

    def _strat_fn(price_slice):
        return strat.generate_returns(price_slice, **params)

    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df
    n_splits = 4
    chunks = np.array_split(df_idx.index, n_splits)
    wf_results = []
    for chunk in chunks:
        if len(chunk) == 0:
            continue
        slice_df = df_idx.loc[chunk]
        r = _strat_fn(slice_df.reset_index())
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

    matching = [c for c in cells if c["symbol"] == symbol and c["vol_regime"] == "low" and c["sharpe"] is not None]
    param_grid_results = {str(c["params"]): c["sharpe"] for c in matching}
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)

    all_results[f"{asset_class}_{symbol}"] = {
        k: {"passed": p, "evidence": e} for k, (p, e) in results.items()
    }
    print(f"=== {asset_class}_{symbol} ===")
    for k, (p, e) in results.items():
        print(k, p, e)

with open("validators_darvas_volconfirm.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
