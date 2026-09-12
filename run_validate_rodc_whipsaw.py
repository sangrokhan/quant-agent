import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from datetime import datetime
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "rodc_strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-12_rodc_whipsaw_gated_ema.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)
from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
best_params = dict(fast_ema=10, slow_ema=30, rodc_max=30.0)

report = {}
for symbol in ["SPY", "QQQ"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **best_params)
    positions = strat.generate_signals(price_df, **best_params)
    num_trades = int((positions.diff() == 1).sum())

    sharpe_p, sharpe_e = check_sharpe_ratio(returns)
    mdd_p, mdd_e = check_max_drawdown(returns)
    tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

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
        r = strat.generate_returns(slice_df, **best_params)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_p = bool(wf_pass_fraction >= 0.75)
    wf_e = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install",
    }

    sens_grid = {}
    for rm in [20.0, 25.0, 30.0, 35.0, 40.0]:
        r = strat.generate_returns(price_df, fast_ema=10, slow_ema=30, rodc_max=rm)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        sens_grid[str(rm)] = float(sh) if sh is not None else 0.0
    sens_p, sens_e = check_parameter_sensitivity(sens_grid)

    report[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_p, **sharpe_e},
        "max_drawdown": {"passed": mdd_p, **mdd_e},
        "transaction_cost_survival": {"passed": tc_p, **tc_e},
        "walk_forward": {"passed": wf_p, **wf_e},
        "parameter_sensitivity": {"passed": sens_p, **sens_e},
    }

with open("validators_rodc_whipsaw.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
