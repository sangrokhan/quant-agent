import sys, json, importlib.util
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-17_ath_chandelier_volgate.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity

BEST = {"atr_multiplier": 4.0, "vol_regime_ratio": 0.9}

results = {}
for sym in ["QQQ", "SPY"]:
    df = load_equity(sym, datetime(2018,1,1), datetime(2026,9,1))
    returns = strat.generate_returns(df, **BEST)
    sig = strat.generate_signals(df, **BEST)
    num_trades = int((sig.diff() == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    # manual date-slice walk-forward fallback (vectorbt.utils.splitting API bug, per prior log entries)
    import vectorbt as vbt
    n_splits = 4
    idx = df.set_index("timestamp").sort_index().index if "timestamp" in df.columns else df.sort_index().index
    chunk = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = idx[i*chunk]
        e = idx[-1] if i == n_splits - 1 else idx[(i+1)*chunk - 1]
        sl = df[(df["timestamp"] if "timestamp" in df.columns else df.index) >= s]
        sl = sl[(sl["timestamp"] if "timestamp" in sl.columns else sl.index) <= e]
        if len(sl) < 30:
            continue
        r = strat.generate_returns(sl, **BEST)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_frac = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = wf_frac >= 0.75
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_frac, "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results, "note": "manual date-slice fallback due to vectorbt.utils.splitting API bug"}

    # parameter sensitivity from grid results for this symbol (atr_multiplier sweep, vol_regime_ratio fixed at best)
    param_results = {}
    for am in [2.5, 3.0, 4.0]:
        r = strat.generate_returns(df, atr_multiplier=am, vol_regime_ratio=BEST["vol_regime_ratio"])
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        param_results[str(am)] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_results)

    results[sym] = {
        "sharpe_ratio": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
        "num_trades": num_trades,
    }

with open("validate_result_ath_chandelier_volgate.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
