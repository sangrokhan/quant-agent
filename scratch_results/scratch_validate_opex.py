import sys, importlib.util, json
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from datetime import datetime
from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
)

spec = importlib.util.spec_from_file_location(
    "opex", "strategies/2026-09-20_opex_third_friday_short.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(day_min=15, day_max=21, quarterly_only=False)

for symbol in ["QQQ", "SPY"]:
    price = load_equity(symbol, datetime(2019, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(price, **params)

    sharpe_ok, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_ok, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    sig = strat.generate_signals(price, **params)
    num_trades = int((sig == -1).sum())
    tc_ok, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades)

    df_idx = price.set_index("timestamp") if "timestamp" in price.columns else price
    n_splits = 4
    step = len(df_idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * step
        e = len(df_idx) if i == n_splits - 1 else (i + 1) * step
        slice_df = df_idx.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **params)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_ok = bool(wf_pass_fraction >= 0.75)
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
             "n_splits": n_splits, "per_split_passed": wf_results}

    out = {
        "symbol": symbol,
        "params": params,
        "num_trades": num_trades,
        "sharpe": [sharpe_ok, sharpe_ev],
        "mdd": [mdd_ok, mdd_ev],
        "tc": [tc_ok, tc_ev],
        "walk_forward": [wf_ok, wf_ev],
    }
    print(json.dumps(out, indent=2, default=str))
    with open(f"validate_result_opex_short_{symbol.lower()}.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
