import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from loaders import load_equity
import importlib.util
import vectorbt as vbt

spec_path = "strategies/2026-09-23_extreme_day_rank_reversal.py"
mspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

start, end = datetime(2019,1,1), datetime(2026,9,1)
best_params = dict(n_extreme=25, hold_days=10)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end, interval="1d")
    returns = strat.generate_returns(price_df, **best_params)
    positions = strat.generate_signals(price_df, **best_params)
    num_trades = int((positions.diff() == 1).sum())

    sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_e = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

    # manual walk-forward (vbt.utils.splitting broken in this env)
    n_splits = 4
    idx = price_df.set_index("timestamp").index if "timestamp" in price_df.columns else price_df.index
    chunk = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        sl = idx[i * chunk: (i + 1) * chunk if i < n_splits - 1 else len(idx)]
        df_slice = price_df.set_index("timestamp").loc[sl].reset_index() if "timestamp" in price_df.columns else price_df.loc[sl]
        r = strat.generate_returns(df_slice, **best_params)
        if r.abs().sum() == 0:
            continue
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        wf_results.append(sh is not None and sh > 0)
    wf_pf = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_p = bool(wf_pf >= 0.75)
    wf_e = {"metric": "walk_forward_pass_fraction", "value": wf_pf, "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results}

    sens = {}
    for ne in [15, 25, 35]:
        for hd in [5, 10, 15]:
            r = strat.generate_returns(price_df, n_extreme=ne, hold_days=hd)
            if r.abs().sum() == 0:
                continue
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            sens[f"ne{ne}_hd{hd}"] = float(sh) if sh is not None else 0.0
    sens_p, sens_e = check_parameter_sensitivity(sens, max_relative_std=0.5)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sharpe_e, "sharpe_passed": sharpe_p,
        "mdd": mdd_e, "mdd_passed": mdd_p,
        "tc": tc_e, "tc_passed": tc_p,
        "wf": wf_e, "wf_passed": wf_p,
        "sensitivity": sens_e, "sensitivity_passed": sens_p,
    }

with open("validate_result_extreme_day_rank_reversal.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
