import sys, json
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-21_bullish_meeting_lines_reversal.py"
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_walk_forward, check_parameter_sensitivity

PARAMS = dict(trend_lookback=10, match_tolerance=0.005, target_atr_mult=1.5)
results = {}
for symbol, loader, ac in [("QQQ", load_equity, "equity"), ("SPY", load_equity, "equity"),
                            ("BTC/USDT", load_crypto, "crypto"), ("ETH/USDT", load_crypto, "crypto")]:
    df = loader(symbol, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    returns = strat.generate_returns(df, **PARAMS)
    position = strat.generate_signals(df, **PARAMS)
    num_trades = int((position.diff().abs() > 0).sum())
    sharpe = check_sharpe_ratio(returns)
    mdd = check_max_drawdown(returns)
    tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    def strat_fn(price_slice):
        return strat.generate_returns(price_slice, **PARAMS)
    try:
        wf = check_walk_forward(df, strat_fn, n_splits=4)
    except Exception as e:
        wf = (None, {"error": str(e)})
    try:
        import vectorbt as vbt
        pgrid = {}
        for mt in [0.003, 0.005, 0.01]:
            p2 = dict(PARAMS); p2["match_tolerance"] = mt
            r2 = strat.generate_returns(df, **p2)
            sh = r2.vbt.returns(freq="D").sharpe_ratio()
            pgrid[str(mt)] = float(sh) if sh is not None else 0.0
        ps = check_parameter_sensitivity(pgrid)
    except Exception as e:
        ps = (None, {"error": str(e)})
    results[symbol] = {"asset_class": ac, "num_trades": num_trades, "sharpe": sharpe, "max_drawdown": mdd, "tc_survival": tc, "walk_forward": wf, "param_sensitivity": ps}

with open("validate_result_bullish_meeting_lines.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
