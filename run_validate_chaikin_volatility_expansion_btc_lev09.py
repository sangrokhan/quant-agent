import sys, os, json
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, ".")
from data.loaders import load_crypto
import importlib.util
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity

spec_mod_path = "strategies/2026-09-24_chaikin_volatility_expansion.py"
spec = importlib.util.spec_from_file_location("strat_cv", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2019,1,1); end = datetime(2026,9,1)
price_df = load_crypto("BTC/USDT", start, end, interval="1d")
params = dict(cv_ema_period=10, cv_lookback=15, rsi_bull_threshold=55, max_hold_days=20, leverage_cap=0.9)
signals = strat.generate_signals(price_df, **{k:v for k,v in params.items() if k!='leverage_cap'})
num_trades = int((signals.diff().abs()==1).sum())
returns = strat.generate_returns(price_df, **params)

out = {}
out["sharpe_ratio"] = check_sharpe_ratio(returns)
out["max_drawdown"] = check_max_drawdown(returns)
out["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

n = len(price_df); splits=4; size=n//splits; results=[]
import vectorbt as vbt
for i in range(splits):
    lo=i*size; hi = n if i==splits-1 else (i+1)*size
    slice_df = price_df.iloc[lo:hi]
    if slice_df.empty: continue
    r = strat.generate_returns(slice_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    results.append(sh)
pf = sum(1 for s in results if s and s>0)/len(results)
out["walk_forward"] = (bool(pf>=0.75), {"metric":"walk_forward_pass_fraction","value":pf,"threshold":0.75,"n_splits":splits,"per_split_sharpe":results})

grid_cells = json.load(open("grid_cells_chaikin_volatility_expansion.json"))
sym_cells = [c for c in grid_cells if c["symbol"]=="BTC/USDT"]
pgr = {}
for c in sym_cells:
    key = json.dumps(c["params"], sort_keys=True)
    pgr.setdefault(key, []).append(c["sharpe"])
avg = {k: sum(v)/len(v) for k,v in pgr.items()}
out["parameter_sensitivity"] = check_parameter_sensitivity(avg)

print(json.dumps({k:[v[0],v[1]] for k,v in out.items()}, indent=2, default=str))
with open("validate_result_chaikin_volatility_expansion_BTC_USDT_lev09.json","w") as f:
    json.dump({k:[v[0],v[1]] for k,v in out.items()}, f, indent=2, default=str)
