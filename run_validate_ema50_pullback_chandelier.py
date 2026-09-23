import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-23_ema50_pullback_group_chandelier_breakeven.py"
spec = importlib.util.spec_from_file_location("strat_emapb", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(pullback_min_bars=2, breakout_atr_mult=0.5, chandelier_mult=2.5)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
qqq = load_equity("QQQ", start, end)

returns = strat.generate_returns(qqq, **params)
signals = strat.generate_signals(qqq, **params)
num_trades = int((signals.diff() == 1).sum())

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

def strat_fn(df):
    return strat.generate_returns(df, **params)

try:
    wf_pass, wf_ev = check_walk_forward(qqq, strat_fn, n_splits=4, min_pass_fraction=0.75)
except AttributeError:
    n_splits = 4
    pdf_sorted = (qqq.set_index("timestamp") if "timestamp" in qqq.columns else qqq).sort_index()
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
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = pass_fraction >= 0.75
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable)",
    }

# param sensitivity from grid cells json (QQQ low-vol nearby cells)
with open("grid_cells_ema50_pullback_chandelier.json") as f:
    cells = json.load(f)
grid_results = {}
for c in cells:
    if c["symbol"] == "QQQ" and c["vol_regime"] == "low":
        key = str(c["params"])
        grid_results[key] = c["sharpe"]
ps_pass, ps_ev = check_parameter_sensitivity(grid_results, max_relative_std=0.5)

out = {
    "params": params,
    "num_trades": num_trades,
    "sharpe": {"passed": sharpe_pass, **sharpe_ev},
    "max_drawdown": {"passed": mdd_pass, **mdd_ev},
    "tc_survival": {"passed": tc_pass, **tc_ev},
    "walk_forward": {"passed": wf_pass, **wf_ev},
    "param_sensitivity": {"passed": ps_pass, **ps_ev},
}
with open("validate_result_ema50_pullback_chandelier_qqq.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
