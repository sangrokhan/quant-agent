import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity, load_crypto  # noqa: E402
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(__file__), "strategies", "2026-09-24_vwap_band_reversal_candle_confirmed.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start = datetime(2019, 1, 1)
end = datetime(2026, 9, 1)

best_params = dict(band_std=2.0, wick_ratio_min=0.5, confirm_window=2)

results = {}
for symbol, loader in [("QQQ", load_equity), ("SPY", load_equity)]:
    price_df = loader(symbol, start, end, interval="1d")
    full_returns = strat.generate_returns(price_df, **best_params)

    sharpe_passed, sharpe_ev = check_sharpe_ratio(full_returns, min_sharpe=1.0)
    mdd_passed, mdd_ev = check_max_drawdown(full_returns, max_allowed_mdd=0.25)

    position = strat.generate_signals(price_df, **best_params)
    num_trades = int((position.diff() == 1).sum())
    tc_passed, tc_ev = check_transaction_cost_survival(full_returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    import vectorbt as vbt
    n = len(price_df)
    n_splits = 4
    size = n // n_splits
    wf_results = []
    for i in range(n_splits):
        lo = i * size
        hi = n if i == n_splits - 1 else (i + 1) * size
        slice_df = price_df.iloc[lo:hi]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **best_params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh)
    wf_pass_fraction = sum(1 for s in wf_results if s and s > 0) / len(wf_results)
    wf_passed = bool(wf_pass_fraction >= 0.75)
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "n_splits": n_splits, "per_split_sharpe": wf_results}

    # parameter sensitivity from grid results for this symbol
    with open("grid_result_vwap_band_reversal.json") as f:
        cells = json.load(f)
    sharpes = {}
    for c in cells:
        if c["symbol"] == symbol and c["error"] is None and c["sharpe"] is not None:
            key = str(c["params"])
            sharpes.setdefault(key, []).append(c["sharpe"])
    avg_sharpes = {k: sum(v)/len(v) for k, v in sharpes.items()}
    ps_passed, ps_ev = check_parameter_sensitivity(avg_sharpes, max_relative_std=0.5)

    results[symbol] = {
        "sharpe": {"passed": sharpe_passed, **sharpe_ev},
        "max_drawdown": {"passed": mdd_passed, **mdd_ev},
        "transaction_cost": {"passed": tc_passed, **tc_ev},
        "walk_forward": {"passed": wf_passed, **wf_ev},
        "parameter_sensitivity": {"passed": ps_passed, **ps_ev},
        "num_trades": num_trades,
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_vwap_band_reversal.json", "w") as f:
    json.dump(results, f, default=str, indent=2)
