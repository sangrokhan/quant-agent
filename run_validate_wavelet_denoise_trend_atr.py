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

spec_path = "strategies/2026-09-16_wavelet_denoise_trend_atr.py"
mspec = importlib.util.spec_from_file_location("wavelet_strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

configs = {
    "QQQ": ("equity", {"wavelet_window": 60, "atr_mult": 0.0}),
    "SPY": ("equity", {"wavelet_window": 60, "atr_mult": 0.0}),
    "BTC/USDT": ("crypto", {"wavelet_window": 60, "atr_mult": 0.0}),
    "ETH/USDT": ("crypto", {"wavelet_window": 60, "atr_mult": 0.0}),
}

all_results = {}
for sym, (asset_class, params) in configs.items():
    if asset_class == "equity":
        price_df = load_equity(sym, start, end)
    else:
        price_df = load_crypto_daily(sym, start, end)

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
             "n_splits": n_splits, "per_split_passed": wf_results}

    param_grid_results = {}
    for ww in [45, 60, 75]:
        for am in [0.0, 0.25]:
            r = strat.generate_returns(price_df, wavelet_window=ww, atr_mult=am)
            import vectorbt as vbt
            s = r.vbt.returns(freq="1D").sharpe_ratio()
            param_grid_results[f"ww{ww}_am{am}"] = float(s) if s is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    all_results[sym] = {
        "params": params,
        "sharpe_ratio": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": cost_pass, **cost_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
    }

with open("validators_wavelet_denoise_trend_atr.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(json.dumps(all_results, indent=2, default=str))
