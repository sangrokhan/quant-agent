"""Strategy: Naive SMA(20) Crossover with Hard 8% Stop-Loss (crypto-focused).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per a Medium article by Kryptera, "I Found a 'Naive' Trend Strategy on
Reddit. I Backtested It on BTC and SOL."
(https://medium.com/@Kryptera/i-found-a-naive-trend-strategy-on-reddit-d02a831f4bf4,
browser_exec fallback -- web_search DDGS backend TLS/connection-reset
errors this iteration), a Reddit poster's viral claim: "long when price
crosses above its 20-day moving average, exit when it crosses back below,
cap the damage with an 8% stop" across a few crypto pairs, reportedly
showing triple-digit CAGRs, a win rate under 40%, and a deep drawdown.
Source's own disclosed rules (translated to vectorbt): Long: close crosses
above SMA(20). Exit: close crosses back below SMA(20) OR an 8% hard stop
from entry price, whichever comes first. Tested by the source on BTC-USD
and SOL-USD over the last 3 years. The article's own framing (title
implies the result "wasn't what expected" when compared to buy-and-hold)
suggests the source itself found this less impressive once benchmarked --
this entry independently re-tests the exact disclosed mechanical rule on
this repo's own crypto pairs (BTC/USDT, ETH/USDT) and equity (QQQ, SPY)
for comparison, rather than taking the Reddit poster's original claim at
face value.

This is the first strategy in this repo combining a bare SMA(20)
crossover (no secondary trend filter, no volatility scaling) with a HARD
PERCENTAGE stop-loss from entry price (rather than a time-stop, a
regime-flip exit, or an ATR-based stop) -- every other SMA-crossover
variant already tested here uses either a longer trend-filter SMA, a
time-stop, or an ATR-multiple stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 20,
    stop_pct: float = 0.08,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: close crosses above SMA(sma_window).
    Exit: close crosses back below SMA(sma_window) OR close has fallen
    stop_pct below the entry price (whichever comes first).
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    above = close > sma
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & (above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = None
    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            stop_hit = px <= entry_price * (1 - stop_pct)
            if bool(cross_down.iloc[i]) or stop_hit:
                in_position = False
                entry_price = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                entry_price = px
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
