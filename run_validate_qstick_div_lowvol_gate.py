import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

import importlib.util
from datetime import datetime
import json

spec = importlib.util.spec_from_file_location("qstick_gated_strat", "strategies/2026-09-28_qstick_bullish_divergence_lowvol_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

configs = {
    "QQQ": (load_equity, {"qstick_window": 14, "swing_lookback": 20, "vol_regime_ratio": 0.9, "max_hold_days": 15}),
    "ETH/USDT": (load_crypto, {"qstick_window": 14, "swing_lookback": 15, "vol_regime_ratio": 0.9, "max_hold_days": 15}),
}

results = {}
for symbol, (loader, params) in configs.items():
    price_df = loader(symbol, start, end, interval="1d")
    returns = strat.generate_returns(price_df, **params)
    sig = strat.generate_signals(price_df, **params)
    num_trades = int((sig.diff().abs() == 1).sum())

    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)
    try:
        wf_p, wf_ev = check_walk_forward(price_df, lambda df: strat.generate_returns(df, **params), n_splits=4, min_pass_fraction=0.75)
    except Exception as exc:
        n = len(price_df)
        splits_idx = [price_df.index[i * n // 4 : (i + 1) * n // 4] for i in range(4)]
        per_split_passed = []
        for idx in splits_idx:
            slice_df = price_df.loc[idx]
            if len(slice_df) < 30:
                continue
            r = strat.generate_returns(slice_df, **params)
            import vectorbt as vbt  # noqa
            sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
            per_split_passed.append(bool(sharpe is not None and sharpe > 0))
        pass_fraction = (sum(per_split_passed) / len(per_split_passed)) if per_split_passed else 0.0
        wf_p = bool(pass_fraction >= 0.75)
        wf_ev = {"metric": "walk_forward_pass_fraction", "value": pass_fraction, "threshold": 0.75,
                 "n_splits": 4, "per_split_passed": per_split_passed,
                 "note": f"manual chronological split fallback (vectorbt API error: {exc})"}

    cells = json.load(open("grid_cells_qstick_div_lowvol_gate.json"))
    pg = {}
    for c in cells:
        if c["symbol"] == symbol and c["sharpe"] is not None:
            pg.setdefault(json.dumps(c["params"], sort_keys=True), []).append(c["sharpe"])
    pg_avg = {k: sum(v) / len(v) for k, v in pg.items()}
    ps_p, ps_ev = check_parameter_sensitivity(pg_avg, max_relative_std=0.5)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": (sharpe_p, sharpe_ev),
        "mdd": (mdd_p, mdd_ev),
        "tc": (tc_p, tc_ev),
        "wf": (wf_p, wf_ev),
        "ps": (ps_p, ps_ev),
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_qstick_div_lowvol_gate.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
