import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity
from data.loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-10_donchian_volume_surge_candle_quality.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

price_df = load_equity("QQQ", datetime(2019,1,1), datetime(2026,9,1))
params = dict(donchian_window=15, vol_surge_mult=1.5, min_body_ratio=0.5)
returns = strat.generate_returns(price_df, **params)

sharpe_passed, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_passed, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
positions = strat.generate_signals(price_df, **params)
num_trades = int((positions.diff().abs() == 1).sum())
tc_passed, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

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
wf_passed = bool(wf_pass_fraction >= 0.75)
wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
         "n_splits": n_splits, "per_split_passed": wf_results,
         "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)"}

# parameter sensitivity from grid cells json (equity/QQQ only, full-sample would be better but reuse grid cells low regime as proxy is wrong; recompute properly)
import itertools
param_grid_results = {}
for dw in [15,20,25]:
    for vm in [1.5,2.0]:
        for mb in [0.5,0.6]:
            p = dict(donchian_window=dw, vol_surge_mult=vm, min_body_ratio=mb)
            r = strat.generate_returns(price_df, **p)
            try:
                s = r.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                s = None
            if s is not None:
                param_grid_results[str(p)] = float(s)

ps_passed, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

out = {
    "num_trades": num_trades,
    "sharpe": [sharpe_passed, sharpe_ev],
    "mdd": [mdd_passed, mdd_ev],
    "tc": [tc_passed, tc_ev],
    "wf": [wf_passed, wf_ev],
    "ps": [ps_passed, ps_ev],
}
print(json.dumps(out, indent=2, default=str))
with open("validators_donchian_volume_surge.json","w") as f:
    json.dump(out, f, indent=2, default=str)
