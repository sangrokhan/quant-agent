import sys, os, json
from datetime import datetime
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward,
)
from data.loaders import load_equity, load_crypto

spec = importlib.util.spec_from_file_location(
    "cup_strat", "strategies/2026-09-28_cup_with_handle_breakout.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

configs = {
    "QQQ": (load_equity, dict(cup_window=40, handle_max_days=15, target_pct=0.5)),
    "BTC/USDT": (load_crypto, dict(cup_window=60, handle_max_days=15, target_pct=0.5)),
}

all_results = {}
for sym, (loader, params) in configs.items():
    df = loader(sym, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df

    returns = strat.generate_returns(df, **params)
    sig = strat.generate_signals(df, **params)
    num_trades = int((sig.diff().fillna(0).clip(lower=0)).sum())

    evidence = {}
    evidence["sharpe"] = check_sharpe_ratio(returns, min_sharpe=1.0)
    evidence["mdd"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
    evidence["tc_survival"] = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=max(num_trades, 1), min_net_sharpe=0.5
    )

    try:
        evidence["walk_forward"] = check_walk_forward(
            df_idx, lambda slice_df: strat.generate_returns(slice_df.reset_index(), **params),
            n_splits=4, min_pass_fraction=0.75,
        )
    except AttributeError:
        n_splits = 4
        pdf_sorted = df_idx.sort_index()
        chunk_len = len(pdf_sorted) // n_splits
        wf_results = []
        for i in range(n_splits):
            lo = i * chunk_len
            hi = len(pdf_sorted) if i == n_splits - 1 else (i + 1) * chunk_len
            slice_df = pdf_sorted.iloc[lo:hi].reset_index()
            if slice_df.empty:
                continue
            r = strat.generate_returns(slice_df, **params)
            import vectorbt as vbt  # noqa
            sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
            wf_results.append(sharpe is not None and sharpe > 0)
        pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
        evidence["walk_forward"] = (pass_fraction >= 0.75, {
            "metric": "walk_forward_pass_fraction", "value": pass_fraction,
            "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
            "note": "manual fallback split",
        })

    all_results[sym] = {k: (v if not isinstance(v, tuple) else [v[0], v[1]]) for k, v in evidence.items()}
    all_results[sym]["num_trades"] = num_trades
    all_results[sym]["params"] = params

print(json.dumps(all_results, indent=2, default=str))
with open("/tmp/cup_validators.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
