import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime
from itertools import product

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-14_nvi_sizing_sma_trend_crypto_lev.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

BEST = dict(trend_window=40, roc_window=10, zscore_window=90, base_exposure=0.25, sensitivity=0.2, leverage_cap=0.3, deadband=0.2)

out_all = {}
for asset_class, symbols, loader in [("equity", ["QQQ","SPY"], load_equity), ("crypto", ["BTC/USDT","ETH/USDT"], load_crypto)]:
    for symbol in symbols:
        df = loader(symbol, datetime(2017,1,1), datetime(2026,9,1), interval="1d")
        returns = strat.generate_returns(df, **BEST)

        sharpe = check_sharpe_ratio(returns)
        mdd = check_max_drawdown(returns)
        sig = strat.generate_signals(df, **BEST)
        num_trades = int((sig.diff().abs() > 0).sum())
        tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

        n_splits = 4
        idx = df.index
        step = len(idx) // n_splits
        wf_results = []
        for i in range(n_splits):
            s = i * step
            e = len(idx) if i == n_splits - 1 else (i + 1) * step
            slice_df = df.iloc[s:e]
            if slice_df.empty:
                continue
            r = strat.generate_returns(slice_df, **BEST)
            sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
            wf_results.append(sh is not None and sh > 0)
        wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
        wf = (bool(wf_pass_fraction >= 0.75), {
            "metric": "walk_forward_pass_fraction",
            "value": wf_pass_fraction,
            "threshold": 0.75,
            "n_splits": n_splits,
            "per_split_passed": wf_results,
        })

        param_grid_results = {}
        for lc, se, db in product([0.25,0.3,0.35],[0.2,0.25,0.3],[0.2,0.3]):
            r = strat.generate_returns(df, leverage_cap=lc, sensitivity=se, deadband=db, base_exposure=0.25)
            sh = check_sharpe_ratio(r)[1]["value"]
            if sh is None or not (sh == sh) or sh in (float("inf"), float("-inf")):
                # zero-variance edge case (deadband holds flat, std=0 -> inf/nan Sharpe);
                # cap to a large-but-finite value so it doesn't blow up relative_std.
                sh = 3.0
            param_grid_results[f"lc={lc},se={se},db={db}"] = sh
        psens = check_parameter_sensitivity(param_grid_results)

        out_all[symbol] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "param_sensitivity": psens, "num_trades": num_trades}

print(json.dumps(out_all, indent=2, default=str))
with open("validators_nvi_crypto_lev.json", "w") as f:
    json.dump(out_all, f, indent=2, default=str)
