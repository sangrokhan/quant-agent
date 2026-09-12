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

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-13_vix_newhigh_rsi_confirm.py"), "vixnh_strat")

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

BEST_PARAMS = {"vix_high_window": 20, "vix_rsi_threshold": 70}

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
        r = strat.generate_returns(slice_df.reset_index(), **BEST_PARAMS)
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

    param_grid_results = {}
    for hw in [15, 20, 30]:
        for th in [60, 65, 70]:
            r2 = strat.generate_returns(price_df, vix_high_window=hw, vix_rsi_threshold=th)
            import vectorbt as vbt
            sh2 = r2.vbt.returns(freq="D").sharpe_ratio()
            param_grid_results[f"hw={hw},th={th}"] = float(sh2) if sh2 is not None else 0.0
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
with open(os.path.join(ROOT, "validators_result_vix_newhigh_rsi.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
