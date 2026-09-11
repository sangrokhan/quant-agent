"""Strategy: Chande's TrendScore, oversold-to-bullish zero-cross entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-152):
Per Tushar Chande, Stocks & Commodities (Sep 1993), as described by
https://theforexgeek.com/trend-score-indicator/ and
https://www.tradingpedia.com/forex-trading-indicators/chandes-trendscore/
(both agree on the mechanics): TrendScore compares the current closing
price against the closing prices of each of the previous `lookback` (20)
periods, ranges -10..+10, with the source's own disclosed trading rule:
"If the blue line of the Trend Score Indicator rises above the zero signal
line from the oversold zone (below the -5 level), you may go long... you
could cancel your buy orders if the blue line falls below the 5 level
during a bullish trend."

Formula (standard sign-count construction matching the source's own -10..+10
range for a 20-period lookback, halved since each of the 20 comparisons
contributes +/-0.5): for each of the last `lookback` bars i=1..lookback,
score contribution = +0.5 if close[t] > close[t-i], -0.5 if close[t] <
close[t-i], 0 if equal; TrendScore[t] = sum of contributions (bounded
-lookback/2..+lookback/2, i.e. -10..+10 at lookback=20).

Signal logic (per source's own disclosed rule):
    Entry (long): TrendScore was below `oversold_level` (-5) within the
    last `confirm_window` bars AND has now crossed back above 0.
    Exit: TrendScore crosses back below `overbought_level` (5) after having
    been above it (source's own "cancel buy orders" mirror-exit rule), OR a
    max_hold_days time-stop as a backstop.

First Chande TrendScore strategy in this repo -- distinct from the other
already-tested Chande-family indicators (Qstick/candle-body-momentum,
Chande Momentum Oscillator, Dynamic Momentum Index/adaptive-RSI, Variable
Index Dynamic Average/VIDYA) since TrendScore's defining mechanic is a
sign-count comparison against a rolling window of past closes, not a
smoothed-average or RSI-style up/down ratio.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trend_score(close: pd.Series, lookback: int) -> pd.Series:
    """Sign-count TrendScore: sum over i=1..lookback of 0.5*sign(close[t]-close[t-i])."""
    arr = close.to_numpy(dtype=float)
    n = len(arr)
    scores = np.full(n, np.nan)
    for t in range(lookback, n):
        window = arr[t - lookback:t]  # closes at t-lookback .. t-1
        diffs = arr[t] - window
        scores[t] = 0.5 * np.sign(diffs).sum()
    return pd.Series(scores, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    oversold_level: float = -5.0,
    overbought_level: float = 5.0,
    confirm_window: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    score = _trend_score(close, lookback)

    was_oversold = (score < oversold_level).rolling(confirm_window).max().fillna(0).astype(bool)
    zero_cross_up = (score > 0) & (score.shift(1) <= 0)
    entry = was_oversold.shift(1).fillna(False) & zero_cross_up

    was_overbought = score >= overbought_level
    exit_signal = was_overbought.shift(1).fillna(False) & (score < overbought_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
