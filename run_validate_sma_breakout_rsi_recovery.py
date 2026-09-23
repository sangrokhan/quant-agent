import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_sma_breakout_rsi_recovery_exit.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

SYMBOL = "QQQ"
PARAMS = {"breakout_pct": 0.02, "rsi_exit_threshold": 30}

price_df = load_equity(SYMBOL, start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
returns = strat.generate_returns(price_df, **PARAMS)
signals = strat.generate_signals(price_df, **PARAMS)
num_trades = int((signals.diff().fillna(0) == 1).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)

df_idx = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
try:
    results["walk_forward"] = check_walk_forward(
        df_idx, lambda slice_df: strat.generate_returns(slice_df.reset_index(), **PARAMS),
        n_splits=4, min_pass_fraction=0.75,
    )
except AttributeError:
    import vectorbt as vbt  # noqa
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
        r = strat.generate_returns(slice_df, **PARAMS)
        sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sharpe is not None and sharpe > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    results["walk_forward"] = (pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable)",
    })

cells = json.load(open("grid_cells_sma_breakout_rsi_recovery.json"))
pgr = {}
for c in cells:
    if c["symbol"] == SYMBOL and c["sharpe"] is not None:
        key = str(c["params"])
        pgr.setdefault(key, []).append(c["sharpe"])
pgr_avg = {k: sum(v) / len(v) for k, v in pgr.items()}
results["parameter_sensitivity"] = check_parameter_sensitivity(pgr_avg, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
out["num_trades"] = num_trades
print(json.dumps(out, indent=2, default=str))
with open("validate_result_sma_breakout_rsi_recovery_qqq.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
