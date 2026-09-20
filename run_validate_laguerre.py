import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
from datetime import datetime
from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util

spec_path = "strategies/2026-09-20_laguerre_rsi_adx_filter.py"
modspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(strat)

params = {"buy_level": 25.0, "adx_level": 20.0, "alpha": 0.2}
start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

results = {}
for sym, loader in [("QQQ", load_equity), ("SPY", load_equity)]:
    price_df = loader(sym, start, end, interval="1d")
    returns = strat.generate_returns(price_df, **params)
    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    pos = strat.generate_signals(price_df, **params)
    num_trades = int((pos.diff().abs() == 1).sum())
    cost_p, cost_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)
    try:
        wf_p, wf_ev = check_walk_forward(price_df, lambda pdf: strat.generate_returns(pdf, **params), n_splits=4, min_pass_fraction=0.75)
    except AttributeError:
        # KNOWN BUG (pre-existing, multiple prior iterations hit this): vectorbt's
        # vbt.utils.splitting.RangeSplitter API no longer exists in the installed
        # vectorbt version. Manual date-slice walk-forward fallback (n_splits=4
        # equal contiguous chunks of price_df), matching the documented intent.
        n_splits = 4
        pdf_sorted = price_df.set_index("timestamp").sort_index() if "timestamp" in price_df.columns else price_df.sort_index()
        chunk_len = len(pdf_sorted) // n_splits
        wf_results = []
        for i in range(n_splits):
            lo = i * chunk_len
            hi = len(pdf_sorted) if i == n_splits - 1 else (i + 1) * chunk_len
            slice_df = pdf_sorted.iloc[lo:hi].reset_index()
            if slice_df.empty:
                continue
            ret = strat.generate_returns(slice_df, **params)
            sh = None
            if len(ret) and ret.abs().sum() > 0:
                import vectorbt as vbt  # noqa: F401
                sh = ret.vbt.returns(freq="D").sharpe_ratio()
            wf_results.append(sh is not None and sh > 0)
        pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
        wf_p = bool(pass_fraction >= 0.75)
        wf_ev = {
            "metric": "walk_forward_pass_fraction", "value": pass_fraction,
            "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
            "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)",
        }

    # parameter sensitivity from grid cells (aggregate sharpe per param combo, full sample not per-regime -- use grid pass data)
    cells = json.load(open("grid_cells_laguerre_rsi_adx.json"))
    sub = [c for c in cells if c["symbol"] == sym and c["sharpe"] is not None]
    from collections import defaultdict
    by_p = defaultdict(list)
    for c in sub:
        by_p[json.dumps(c["params"], sort_keys=True)].append(c["sharpe"])
    param_grid_results = {k: sum(v)/len(v) for k, v in by_p.items()}
    sens_p, sens_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[sym] = {
        "sharpe": sharpe_ev, "sharpe_passed": sharpe_p,
        "mdd": mdd_ev, "mdd_passed": mdd_p,
        "cost": cost_ev, "cost_passed": cost_p,
        "walk_forward": wf_ev, "wf_passed": wf_p,
        "param_sensitivity": sens_ev, "sens_passed": sens_p,
        "num_trades": num_trades,
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_laguerre_rsi_adx.json", "w") as f:
    json.dump(results, f, default=str, indent=2)
