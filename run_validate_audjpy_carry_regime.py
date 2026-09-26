import sys, os, json, warnings
warnings.filterwarnings("ignore")
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, "strategies")
from loaders import load_equity, load_crypto
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-26_audjpy_carry_regime_trend_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
PARAMS = {"trend_window": 150, "carry_ma_window": 150, "carry_fast_window": 50}

results = {}
for asset_class, symbol, loader in [
    ("equity", "QQQ", load_equity), ("equity", "SPY", load_equity),
    ("crypto", "BTC/USDT", load_crypto), ("crypto", "ETH/USDT", load_crypto),
]:
    if asset_class == "equity":
        price_df = loader(symbol, start, end, interval="1d")
    else:
        price_df = loader(symbol, start, end, interval="1d")
    returns = strat.generate_returns(price_df, **PARAMS)
    signals = strat.generate_signals(price_df, **PARAMS)
    num_trades = int((signals.diff().abs() == 1).sum())

    sharpe_ok, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_ok, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_ok, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    param_grid_results = {}
    for tw in [50, 100, 150]:
        r = strat.generate_returns(price_df, trend_window=tw, carry_ma_window=PARAMS["carry_ma_window"], carry_fast_window=PARAMS["carry_fast_window"])
        _, s_ev = check_sharpe_ratio(r, min_sharpe=-999)
        param_grid_results[str(tw)] = s_ev["value"]
    ps_ok, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[f"{asset_class}:{symbol}"] = {
        "sharpe": {"passed": sharpe_ok, **sharpe_ev},
        "mdd": {"passed": mdd_ok, **mdd_ev},
        "tc_survival": {"passed": tc_ok, **tc_ev},
        "param_sensitivity": {"passed": ps_ok, **ps_ev},
        "num_trades": num_trades,
        "all_passed": bool(sharpe_ok and mdd_ok and tc_ok and ps_ok),
    }

with open("validate_result_audjpy_carry_regime.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
