import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from data.loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-18_disparity_index_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity
)

configs = {
    "QQQ": (load_equity, dict(trend_window=40, sensitivity=0.6, leverage_cap=0.4, deadband=0.35)),
    "SPY": (load_equity, dict(trend_window=40, sensitivity=0.6, leverage_cap=0.4, deadband=0.35)),
    "BTC/USDT": (load_crypto, dict(trend_window=60, sensitivity=0.6, leverage_cap=0.4, deadband=0.35)),
    "ETH/USDT": (load_crypto, dict(trend_window=40, sensitivity=0.6, leverage_cap=0.4, deadband=0.35)),
}

results = {}
cells = json.load(open("grid_cells_disparity_sizing.json"))
for sym, (loader, params) in configs.items():
    if loader is load_crypto:
        price_df = loader(sym, datetime(2019,1,1), datetime(2026,9,1), interval="1d")
    else:
        price_df = loader(sym, datetime(2019,1,1), datetime(2026,9,1))
    returns = strat.generate_returns(price_df, **params)
    exposure = strat.generate_signals(price_df, **params)
    # approximate num_trades as number of exposure-level changes
    num_trades = int((exposure.diff().abs() > 1e-9).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    df_idx = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
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
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
             "n_splits": n_splits, "per_split_passed": wf_results,
             "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)"}

    pg_results = {}
    for c in cells:
        if c['symbol'] == sym and c['params']['leverage_cap']==params['leverage_cap']:
            key = str(c['params'])
            pg_results.setdefault(key, []).append(c['sharpe'])
    pg_avg = {k: sum(v)/len(v) for k,v in pg_results.items() if v}
    ps_pass, ps_ev = check_parameter_sensitivity(pg_avg)

    results[sym] = dict(
        params=params, num_trades=num_trades,
        sharpe=sharpe_ev, mdd=mdd_ev, tc=tc_ev, wf=wf_ev, param_sens=ps_ev,
        all_passed=all([sharpe_pass, mdd_pass, tc_pass, wf_pass, ps_pass]),
        sharpe_pass=sharpe_pass, mdd_pass=mdd_pass, tc_pass=tc_pass, wf_pass=wf_pass, ps_pass=ps_pass,
    )

print(json.dumps(results, indent=2, default=str))
with open("validators_disparity_sizing.json","w") as f:
    json.dump(results, f, indent=2, default=str)
