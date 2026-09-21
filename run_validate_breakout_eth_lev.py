import sys, os, json
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_crypto
import importlib.util

spec_mod_path = "strategies/2026-09-20_breakout_trend_momentum_gate.py"
spec = importlib.util.spec_from_file_location("strat_bt", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

best_params = dict(breakout_window=25, entry_persist=3, mom_window=63, leverage_cap=0.65)

price_df = load_crypto("ETH/USDT", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1), interval="1d")
returns = strat.generate_returns(price_df, **best_params)

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)

position = strat.generate_signals(price_df, **best_params)
num_trades = int((position.diff().abs() > 0).sum())
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

try:
    def strategy_fn(slice_df):
        return strat.generate_returns(slice_df, **best_params)
    wf_pass, wf_ev = check_walk_forward(price_df, strategy_fn, n_splits=4, min_pass_fraction=0.75)
except AttributeError:
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
        r = strat.generate_returns(slice_df, **best_params)
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

param_grid_results = {}
for bw in [20, 25, 30]:
    for ep in [3, 5]:
        for mw in [63, 90]:
            p = dict(breakout_window=bw, entry_persist=ep, mom_window=mw, leverage_cap=0.65)
            r = strat.generate_returns(price_df, **p)
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            param_grid_results[str(p)] = float(sh) if sh is not None and pd.notna(sh) else 0.0

ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

result = {
    "best_params": best_params,
    "sharpe": {"passed": sharpe_pass, "evidence": sharpe_ev},
    "max_drawdown": {"passed": mdd_pass, "evidence": mdd_ev},
    "transaction_cost_survival": {"passed": tc_pass, "evidence": tc_ev},
    "walk_forward": {"passed": wf_pass, "evidence": wf_ev},
    "parameter_sensitivity": {"passed": ps_pass, "evidence": ps_ev},
}
with open("validate_result_breakout_trend_momentum_eth_lev.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print(json.dumps(result, indent=2, default=str))
