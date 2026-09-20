import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'strategies'); sys.path.insert(0,'validation'); sys.path.insert(0,'data'); sys.path.insert(0,'.')
from datetime import datetime
import importlib.util
spec = importlib.util.spec_from_file_location('strat_mod','strategies/2026-09-20_turn_of_month_seasonality.py')
strat = importlib.util.module_from_spec(spec); spec.loader.exec_module(strat)
from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

symbol = "QQQ"
start, end = datetime(2017,1,1), datetime(2026,9,1)
df = load_equity(symbol, start, end, interval="1d")
params = dict(last_n_days=5, first_n_days=4)
r = strat.generate_returns(df, **params)
pos = strat.generate_signals(df, **params)
num_trades = int((pos.diff().abs() == 1).sum())

sh_pass, sh_ev = check_sharpe_ratio(r)
mdd_pass, mdd_ev = check_max_drawdown(r)
tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=10.0, num_trades=num_trades)

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
    "note": "manual split -- validators.check_walk_forward errors on installed vectorbt (vbt.utils.splitting missing)",
}

sweep = {}
for ln in [4, 5, 6]:
    for fn in [3, 4, 5]:
        rr = strat.generate_returns(df, last_n_days=ln, first_n_days=fn)
        sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
        sweep[f"last_n_days={ln},first_n_days={fn}"] = float(sh) if sh is not None else 0.0
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
with open("validate_result_turn_of_month_qqq.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print(json.dumps(result, indent=2, default=str))
