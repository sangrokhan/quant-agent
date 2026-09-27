import sys, json
sys.path.insert(0,'strategies'); sys.path.insert(0,'validation'); sys.path.insert(0,'data'); sys.path.insert(0,'.')
from datetime import datetime
import importlib.util
spec = importlib.util.spec_from_file_location('strat_mod','strategies/2026-09-27_triple_proxy_avg_zscore_continuous_sizing.py')
strat = importlib.util.module_from_spec(spec); spec.loader.exec_module(strat)
from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

configs = {
    "QQQ": dict(trend_window=30, zscore_window=120, sizing_scale=0.5, deadband=0.15),
    "SPY": dict(trend_window=30, zscore_window=120, sizing_scale=0.5, deadband=0.15),
}

all_results = {}
for symbol, params in configs.items():
    start, end = datetime(2019,1,1), datetime(2026,9,1)
    df = load_equity(symbol, start, end, interval="1d")
    r = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    # For continuous sizing, count meaningful position changes (threshold crossing)
    binary_pos = (pos > 0.01).astype(int)
    num_trades = int((binary_pos.diff().abs() == 1).sum())

    sh_pass, sh_ev = check_sharpe_ratio(r)
    mdd_pass, mdd_ev = check_max_drawdown(r)
    tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=15.0, num_trades=num_trades)

    n_splits = 4
    idx = df.index
    chunk_bounds = [int(i * len(idx) / n_splits) for i in range(n_splits + 1)]
    wf_results = []
    for i in range(n_splits):
        lo, hi = chunk_bounds[i], chunk_bounds[i + 1]
        slice_df = df.iloc[lo:hi]
        if slice_df.empty:
            continue
        rr = strat.generate_returns(slice_df, **params)
        sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = wf_pass_fraction >= 0.75
    wf_ev = {
        "metric": "walk_forward_pass_fraction_manual",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
        "note": "manual split",
    }

    sweep = {}
    for tw in [30, 50]:
        for ss in [0.5, 1.0, 1.5]:
            rr = strat.generate_returns(df, trend_window=tw, zscore_window=params["zscore_window"], sizing_scale=ss, deadband=params["deadband"])
            sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
            sweep[f"trend_window={tw},sizing_scale={ss}"] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(sweep)

    result = {
        "symbol": symbol,
        "params": params,
        "num_trades": num_trades,
        "sharpe_ratio": {"passed": sh_pass, **sh_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
    }
    all_results[symbol] = result

with open("validate_result_triple_proxy_continuous.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(json.dumps(all_results, indent=2, default=str))
