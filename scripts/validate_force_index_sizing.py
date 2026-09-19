import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-20_force_index_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

START = datetime(2019, 1, 1)
END = datetime(2026, 9, 1)

PARAMS = dict(sensitivity=0.4, deadband=0.15)

symbols = {
    "equity": [("QQQ", load_equity), ("SPY", load_equity)],
    "crypto": [("BTC/USDT", load_crypto), ("ETH/USDT", load_crypto)],
}

all_results = {}
for asset_class, sym_loaders in symbols.items():
    for symbol, loader in sym_loaders:
        try:
            price_df = loader(symbol, START, END, interval="1d")
        except TypeError:
            price_df = loader(symbol, START, END)

        returns = strat.generate_returns(price_df, **PARAMS)
        exposure = strat.generate_signals(price_df, **PARAMS)
        num_trades = int((exposure.diff().abs() > 0).sum())

        sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
        mdd_pass, mdd_ev = check_max_drawdown(returns)
        tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

        def strat_fn(slice_df):
            return strat.generate_returns(slice_df, **PARAMS)

        try:
            wf_pass, wf_ev = check_walk_forward(price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df, strat_fn)
        except Exception as e:
            wf_pass, wf_ev = None, {"error": str(e)}

        # parameter sensitivity from grid results already computed (sensitivity x deadband)
        import json as _json
        cells = _json.load(open("grid_cells_force_index_sizing.json"))
        pg = {}
        for c in cells:
            if c["symbol"] == symbol and c["vol_regime_label"] == "low":
                key = f"sens={c['params']['sensitivity']},db={c['params']['deadband']}"
                if c["sharpe"] is not None:
                    pg[key] = c["sharpe"]
        ps_pass, ps_ev = check_parameter_sensitivity(pg) if pg else (None, {})

        all_results[f"{asset_class}:{symbol}"] = {
            "sharpe": {"passed": sharpe_pass, **sharpe_ev},
            "max_drawdown": {"passed": mdd_pass, **mdd_ev},
            "tc_survival": {"passed": tc_pass, **tc_ev},
            "walk_forward": {"passed": wf_pass, **wf_ev},
            "param_sensitivity": {"passed": ps_pass, **ps_ev},
            "num_trades": num_trades,
        }

print(json.dumps(all_results, indent=2, default=str))
with open("validate_result_force_index_sizing.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
