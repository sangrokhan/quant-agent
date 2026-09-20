import sys, importlib.util, json
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from datetime import datetime
from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

spec = importlib.util.spec_from_file_location(
    "crabel_ut", "strategies/2026-09-20_crabel_upthrust_long.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(pivot_left=4, max_hold_days=20, use_rsi_exit=False)

results = {}
for asset_class, symbol, loader in [
    ("equity", "SPY", load_equity), ("equity", "QQQ", load_equity),
    ("crypto", "BTC/USDT", load_crypto), ("crypto", "ETH/USDT", load_crypto),
]:
    if asset_class == "equity":
        price = loader(symbol, datetime(2019, 1, 1), datetime(2026, 9, 1))
    else:
        price = loader(symbol, datetime(2019, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(price, **params)

    sharpe_ok, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_ok, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    sig = strat.generate_signals(price, **params)
    num_trades = int((sig.diff() == 1).sum())
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

    sens_results = {}
    for pl in [4, 6, 10]:
        p2 = dict(params); p2["pivot_left"] = pl
        r2 = strat.generate_returns(price, **p2)
        import vectorbt as vbt
        sh = r2.vbt.returns(freq="D").sharpe_ratio()
        sens_results[f"pivot_left_{pl}"] = float(sh) if sh is not None else 0.0
    sens_ok, sens_ev = check_parameter_sensitivity(sens_results, max_relative_std=0.5)

    out = {
        "symbol": symbol,
        "params": params,
        "num_trades": num_trades,
        "sharpe": [sharpe_ok, sharpe_ev],
        "mdd": [mdd_ok, mdd_ev],
        "tc": [tc_ok, tc_ev],
        "walk_forward": [wf_ok, wf_ev],
        "param_sensitivity": [sens_ok, sens_ev],
    }
    results[symbol] = out
    print(json.dumps(out, indent=2, default=str))

with open("validate_result_crabel_upthrust_all.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
