"""Strategy: Deep Pullback mean-reversion in a confirmed bull market (QuantifiedStrategies.com).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-081):
Per a Google AI-overview synthesis of QuantifiedStrategies.com's "Deep
Pullback Strategy" (browser_exec fallback -- web_search DDGS backend
returns mangled non-English results this iteration; the direct article
page itself was previously found paywalled beyond summary stats in
2026-09-20-072 this same cron trigger, but the AI-overview now discloses
the exact numeric entry/exit rule), a bull-market mean-reversion setup:
buy a temporary deep pullback while the primary trend remains intact.
Disclosed entry rule (all conditions must hold):
    1. Today's close is the LOWEST close of the last `lookback_close`
       (15) trading days.
    2. Today's 1-day return is the LOWEST 1-day return of the last
       `lookback_return` (10) trading days.
    3. Price is still above its `trend_window` (200) day SMA (confirms
       the broader bull-market trend is intact, distinguishing a
       temporary sharp pullback from a genuine trend reversal).
Disclosed exit rule: close today above yesterday's high (a simple
one-day-momentum-confirmation exit -- the source's own SPY backtest
reported this yields short average hold times of only a few days,
78% win rate, profit factor 3.0, only ~5% time invested in the market).
This is a genuinely distinct construction from every existing
"buy-the-dip"/oversold strategy in this repo since it combines a
DUAL extreme-rareness filter (lowest close of N days AND lowest return of
M days simultaneously) with a long-horizon (200d) trend gate and an
asymmetric one-bar momentum-confirmation exit (not a fixed time-stop or
indicator-crossover exit).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    lookback_close: int = 15,
    lookback_return: int = 10,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: today's close is the lowest close of the last
    `lookback_close` days AND today's 1-day return is the lowest of the
    last `lookback_return` days AND close > SMA(trend_window). Exit:
    close today exceeds the prior day's high.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    daily_ret = close.pct_change()
    rolling_min_close = close.rolling(lookback_close).min()
    rolling_min_ret = daily_ret.rolling(lookback_return).min()
    trend_sma = close.rolling(trend_window).mean()

    is_lowest_close = close <= rolling_min_close
    is_lowest_ret = daily_ret <= rolling_min_ret
    above_trend = close > trend_sma

    entry = is_lowest_close & is_lowest_ret & above_trend.fillna(False)
    exit_signal = close > high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.fillna(False).values
    exit_vals = exit_signal.fillna(False).values

    for i in range(len(close)):
        if in_position:
            position.iloc[i] = 1
            if bool(exit_vals[i]):
                in_position = False
        else:
            if bool(entry_vals[i]):
                in_position = True
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
