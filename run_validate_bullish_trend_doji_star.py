import sys, json
from datetime import datetime
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-21_bullish_trend_doji_star_continuation.py"
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival

PARAMS = dict(trend_lookback=10, doji_body_pct=0.10, target_atr_mult=3.0)
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
    results[symbol] = {"asset_class": ac, "num_trades": num_trades, "sharpe": sharpe, "max_drawdown": mdd, "tc_survival": tc}

print(json.dumps(results, indent=2, default=str))
