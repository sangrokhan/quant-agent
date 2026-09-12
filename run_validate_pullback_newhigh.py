import sys, os, json, importlib.util
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "validation"))
sys.path.insert(0, os.path.join(ROOT, "data"))

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-13_pullback_to_newhigh_trend.py"), "pb_strat")

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

BEST_PARAMS = {"pullback_pct": 0.20, "exit_lookback": 90}

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **BEST_PARAMS)

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)

    position = strat.generate_signals(price_df, **BEST_PARAMS)
    num_trades = int((position.diff().fillna(0) == 1).sum())
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

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
        r = strat.generate_returns(slice_df, **BEST_PARAMS)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install",
    }

    # param sensitivity from grid results (reuse grid json)
    with open(os.path.join(ROOT, "grid_result_pullback_newhigh.json")) as f:
        grid_summary = json.load(f)

    # Build param_grid_results from full grid run in-process for this symbol
    param_grid_results = {}
    for pb in [0.10, 0.15, 0.20]:
        for el in [40, 60, 90]:
            r = strat.generate_returns(price_df, pullback_pct=pb, exit_lookback=el)
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            param_grid_results[f"pb={pb},el={el}"] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sharpe_ev, "sharpe_pass": sharpe_pass,
        "mdd": mdd_ev, "mdd_pass": mdd_pass,
        "tc": tc_ev, "tc_pass": tc_pass,
        "walk_forward": wf_ev, "wf_pass": wf_pass,
        "param_sensitivity": ps_ev, "ps_pass": ps_pass,
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(ROOT, "validators_result_pullback_newhigh.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
