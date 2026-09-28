import sys
import json
from datetime import datetime
import importlib.util

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity, load_crypto  # noqa: E402
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)  # noqa: E402

spec_mod = importlib.util.spec_from_file_location(
    "alma_strat", "strategies/2026-09-28_alma_dual_crossover_trend.py"
)
alma_strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(alma_strat)

PARAMS = {"fast_window": 14, "slow_window": 34}
START, END = datetime(2019, 1, 1), datetime(2026, 9, 1)

results = {}
loaders = {"QQQ": ("equity", load_equity), "SPY": ("equity", load_equity),
           "BTC/USDT": ("crypto", load_crypto), "ETH/USDT": ("crypto", load_crypto)}

# param grid results per symbol (using grid_cells json already computed, filtered per symbol full-sample)
grid_cells = json.load(open("grid_cells_alma_dual_crossover.json"))

for symbol, (ac, loader) in loaders.items():
    price_df = loader(symbol, START, END, interval="1d")
    returns = alma_strat.generate_returns(price_df, **PARAMS)
    position = alma_strat.generate_signals(price_df, **PARAMS)
    num_trades = int((position.diff() == 1).sum())

    sharpe_passed, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_passed, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_passed, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    # Manual 4-split walk-forward (vectorbt's RangeSplitter API unavailable
    # in this installed version -- established repo workaround, see e.g.
    # 2026-09-06-120's notes: "walk-forward manual 4-split").
    n_splits = 4
    n = len(price_df)
    split_size = n // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * split_size
        e = n if i == n_splits - 1 else (i + 1) * split_size
        slice_df = price_df.iloc[s:e]
        if len(slice_df) < 30:
            continue
        r = alma_strat.generate_returns(slice_df, **PARAMS)
        _, sh_ev = check_sharpe_ratio(r, min_sharpe=-999)
        wf_results.append(sh_ev["value"] is not None and sh_ev["value"] > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_passed = wf_pass_fraction >= 0.75
    wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction,
              "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results}

    # param sensitivity: use grid sharpe values per symbol across param combos (avg across vol regimes per earlier agg, but here recompute full-sample per combo)
    param_results = {}
    for fw in [7, 9, 14]:
        for sw in [21, 34, 50]:
            p = {"fast_window": fw, "slow_window": sw}
            r = alma_strat.generate_returns(price_df, **p)
            sh_passed, sh_ev = check_sharpe_ratio(r, min_sharpe=-999)
            param_results[str(p)] = sh_ev["value"] if sh_ev["value"] is not None else 0.0
    ps_passed, ps_ev = check_parameter_sensitivity(param_results, max_relative_std=0.5)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sharpe_ev, "sharpe_passed": sharpe_passed,
        "mdd": mdd_ev, "mdd_passed": mdd_passed,
        "tc": tc_ev, "tc_passed": tc_passed,
        "wf": wf_ev, "wf_passed": wf_passed,
        "ps": ps_ev, "ps_passed": ps_passed,
        "all_passed": sharpe_passed and mdd_passed and tc_passed and wf_passed and ps_passed,
    }
    print(symbol, "ALL PASSED:" if results[symbol]["all_passed"] else "FAILED:",
          "Sharpe=%.3f MDD=%.3f TC_net_sharpe=%.3f WF=%.2f PS_relstd=%.3f trades=%d" % (
              sharpe_ev["value"], mdd_ev["value"], tc_ev["value"], wf_ev["value"], ps_ev["value"], num_trades))

with open("validate_result_alma_dual_crossover.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
