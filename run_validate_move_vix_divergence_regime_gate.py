import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-24_move_vix_divergence_regime_gate.py"
spec = importlib.util.spec_from_file_location("strat_movevix", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

BEST = {"divergence_threshold": 1.5, "sma_window": 50}
BEST_SPY = {"divergence_threshold": 1.0, "sma_window": 100}

results = {}
for sym in ["SPY", "QQQ"]:
    cfg = BEST_SPY if sym == "SPY" else BEST
    price_df = load_equity(sym, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    ret = strat.generate_returns(price_df, **cfg)
    sharpe_ok, sharpe_ev = check_sharpe_ratio(ret)
    mdd_ok, mdd_ev = check_max_drawdown(ret)
    num_trades = int((ret.abs() > 0).astype(int).diff().abs().sum() / 2) + 1
    tc_ok, tc_ev = check_transaction_cost_survival(ret, cost_bps_per_trade=10, num_trades=num_trades)

    # Manual 4-split date fallback (vbt.utils.splitting.RangeSplitter broken
    # in installed vectorbt==1.1.0, per multiple prior repo entries).
    idx = price_df.set_index("timestamp").index if "timestamp" in price_df.columns else price_df.index
    n = len(idx)
    splits_idx = [idx[int(n*i/4):int(n*(i+1)/4)] for i in range(4)]
    wf_results = []
    for sidx in splits_idx:
        if len(sidx) < 30:
            continue
        slice_df = price_df.set_index("timestamp").loc[sidx].reset_index() if "timestamp" in price_df.columns else price_df.loc[sidx]
        r = strat.generate_returns(slice_df, **cfg)
        _, sev = check_sharpe_ratio(r)
        wf_results.append((sev["value"] or 0.0) > 0)
    wf_pass_frac = sum(wf_results) / len(wf_results) if wf_results else 0.0
    wf_ok = wf_pass_frac >= 0.75
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_frac, "threshold": 0.75, "per_split_passed": wf_results}

    # parameter sensitivity: sweep divergence_threshold and sma_window near best
    param_grid_results = {}
    for dt in [0.5, 1.0, 1.5]:
        for sw in [30, 50, 100]:
            r = strat.generate_returns(price_df, divergence_threshold=dt, sma_window=sw)
            _, ev = check_sharpe_ratio(r)
            param_grid_results[f"dt={dt},sw={sw}"] = ev["value"] or 0.0
    ps_ok, ps_ev = check_parameter_sensitivity(param_grid_results)

    results[sym] = {
        "sharpe": sharpe_ev, "mdd": mdd_ev, "tc": tc_ev, "wf": wf_ev, "ps": ps_ev,
        "sharpe_pass": sharpe_ok, "mdd_pass": mdd_ok, "tc_pass": tc_ok, "wf_pass": wf_ok, "ps_pass": ps_ok,
        "num_trades": num_trades,
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_move_vix_divergence_regime_gate.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
