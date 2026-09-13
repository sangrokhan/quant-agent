import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
import importlib.util
from functools import partial

load_crypto_daily = partial(load_crypto, interval="1d")

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-13_pain_ratio_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("pain_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
best_params = {"pain_ratio_reference": 3.0, "pain_window": 60}

report = {}
for symbol, loader in [("SPY", load_equity), ("QQQ", load_equity), ("BTC/USDT", load_crypto_daily)]:
    price_df = loader(symbol, start, end)
    returns = strat.generate_returns(price_df, **best_params)
    positions = strat.generate_signals(price_df, **best_params)
    entering = (positions > 0) & (positions.shift(1).fillna(0) == 0)
    num_trades = int(entering.sum())

    sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_e = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

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
    wf_e = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
            "n_splits": n_splits, "per_split_passed": wf_results, "note": "manual 4-equal-slice fallback"}

    sens_grid = {}
    for pr in [3.0, 6.0, 10.0]:
        for pw in [60, 90]:
            r = strat.generate_returns(price_df, pain_ratio_reference=pr, pain_window=pw)
            try:
                import vectorbt as vbt
                sh = r.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                sh = None
            sens_grid[str((pr, pw))] = float(sh) if sh is not None else 0.0
    sens_p, sens_e = check_parameter_sensitivity(sens_grid, max_relative_std=0.5)

    report[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_p, **sharpe_e},
        "max_drawdown": {"passed": mdd_p, **mdd_e},
        "transaction_cost_survival": {"passed": tc_p, **tc_e},
        "walk_forward": {"passed": wf_p, **wf_e},
        "parameter_sensitivity": {"passed": sens_p, **sens_e},
    }

with open("validators_pain.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
