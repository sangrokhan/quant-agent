import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-22_inside_day_atr_compression_breakout.py"
spec = importlib.util.spec_from_file_location("strat_idatr", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

BEST_PARAMS = {"atr_compress_pct": 0.05, "target_mult": 2.0}

out_by_symbol = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start=datetime(2019, 1, 1), end=datetime(2026, 9, 1))
    returns = strat.generate_returns(price_df, **BEST_PARAMS)
    position = strat.generate_signals(price_df, **BEST_PARAMS)
    num_trades = int((position.diff().abs() == 1).sum())

    results = {}
    results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
    results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
    results["transaction_cost_survival"] = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
    )

    # Manual 4-split walk-forward (vbt.utils.splitting.RangeSplitter unavailable in this repo)
    n_splits = 4
    pdf_sorted = (price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df).sort_index()
    chunk_len = len(pdf_sorted) // n_splits
    wf_results = []
    for i in range(n_splits):
        lo = i * chunk_len
        hi = len(pdf_sorted) if i == n_splits - 1 else (i + 1) * chunk_len
        slice_df = pdf_sorted.iloc[lo:hi].reset_index()
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **BEST_PARAMS)
        import vectorbt as vbt  # noqa
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    results["walk_forward"] = (pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable)",
    })

    # Parameter sensitivity from the grid cells already computed for this symbol
    grid_cells = json.load(open("grid_cells_inside_day_atr_compression_breakout.json"))
    param_sharpes = {}
    for c in grid_cells:
        if c["symbol"] == symbol and c["sharpe"] is not None:
            key = str(c["params"])
            param_sharpes.setdefault(key, []).append(c["sharpe"])
    param_sharpes_avg = {k: sum(v) / len(v) for k, v in param_sharpes.items()}
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_sharpes_avg, max_relative_std=0.5)

    out_by_symbol[symbol] = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
    out_by_symbol[symbol]["num_trades"] = num_trades

print(json.dumps(out_by_symbol, indent=2, default=str))
with open("validate_result_inside_day_atr_compression_breakout.json", "w") as f:
    json.dump(out_by_symbol, f, indent=2, default=str)
