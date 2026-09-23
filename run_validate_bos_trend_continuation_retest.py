import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_equity, load_crypto
import importlib.util

spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-24_bos_trend_continuation_retest.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

CONFIGS = {
    "BTC/USDT": ("crypto", dict(swing_window=3, retest_window=5, max_hold_days=30)),
    "QQQ": ("equity", dict(swing_window=3, retest_window=5, max_hold_days=20)),
    "SPY": ("equity", dict(swing_window=5, retest_window=5, max_hold_days=20)),
}

all_out = {}
for sym, (asset_class, best_params) in CONFIGS.items():
    loader = load_equity if asset_class == "equity" else load_crypto
    df = loader(sym, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df

    returns = strat.generate_returns(df, **best_params)
    pos = strat.generate_signals(df, **best_params)
    num_trades = int((pos.diff().fillna(0) != 0).sum() / 2) + 1

    evidence = {}
    evidence["sharpe"] = check_sharpe_ratio(returns, min_sharpe=1.0)
    evidence["mdd"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
    evidence["tc_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

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
        r = strat.generate_returns(slice_df, **best_params)
        import vectorbt as vbt  # noqa
        sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sharpe is not None and sharpe > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    evidence["walk_forward"] = (pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split",
    })

    pgr = {}
    for sw in [3, 5]:
        for rw in [5, 10]:
            params = dict(swing_window=sw, retest_window=rw, max_hold_days=best_params["max_hold_days"])
            r = strat.generate_returns(df, **params)
            import vectorbt as vbt  # noqa
            sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
            if sh is not None:
                pgr[str(params)] = float(sh)
    evidence["param_sensitivity"] = check_parameter_sensitivity(pgr, max_relative_std=0.5)

    out = {k: {"passed": v[0], "evidence": v[1]} for k, v in evidence.items()}
    out["num_trades"] = num_trades
    out["params"] = best_params
    all_out[sym] = out
    safe = sym.replace("/", "_").lower()
    with open(f"validate_result_bos_trend_continuation_retest_{safe}.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

print(json.dumps(all_out, indent=2, default=str))
