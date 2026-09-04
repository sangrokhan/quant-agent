"""Strategy: Chaikin Oscillator zero-line cross, gated by a long-term trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-093):
Source (quantifiedstrategies.com/chaikin-oscillator-trading-strategy/) reports
a naive Chaikin Oscillator zero-line-cross strategy (CO = EMA(fast,ADL) -
EMA(slow,ADL), buy CO>0 / sell CO<0) is weak in isolation on the S&P 500
(CAGR ~2.4%/20yr, optimized params 10/20 rather than the "standard" 3/10).
This repo's own prior finding (2026-09-01-001: SMA crossover failed
walk-forward specifically due to regime-dependence) suggests overlaying a
200-day SMA trend filter (only take the CO zero-cross long signal when
price is already above its 200d SMA) should filter out exactly the choppy/
downtrending conditions where the naive zero-cross whipsaws, improving on
the source's own weak baseline result.

Signal logic
------------
- Money Flow Multiplier (MFM) = ((close-low)-(high-close)) / (high-low)
- Money Flow Volume (MFV) = MFM * volume
- Accumulation/Distribution Line (ADL) = cumulative sum of MFV
- Chaikin Oscillator (CO) = EMA(fast_window, ADL) - EMA(slow_window, ADL)
- Entry (long): CO crosses from <=0 to >0 AND close > SMA(trend_window)
- Exit: CO crosses from >0 to <=0, OR price drops below SMA(trend_window)
  (regime-flip exit, consistent with 2026-09-03-001's vol-regime exit
  pattern), OR after max_hold_days trading days.
- Flat (no position) otherwise. Long-only per SAFETY.md.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _chaikin_oscillator(df: pd.DataFrame, fast_window: int, slow_window: int) -> pd.Series:
    high, low, close, vol = df["high"], df["low"], df["close"], df["volume"]
    hl_range = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / hl_range
    mfm = mfm.fillna(0.0)
    mfv = mfm * vol
    adl = mfv.cumsum()
    co = adl.ewm(span=fast_window, adjust=False).mean() - adl.ewm(span=slow_window, adjust=False).mean()
    return co


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 3,
    slow_window: int = 10,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    co = _chaikin_oscillator(df, fast_window, slow_window)
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = close > trend_sma

    co_pos = co > 0
    cross_up = co_pos & (~co_pos.shift(1).fillna(False))
    cross_down = (~co_pos) & (co_pos.shift(1).fillna(False))

    entry = cross_up & above_trend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(cross_down.iloc[i]) or (not bool(above_trend.iloc[i])) or held >= max_hold_days
            if exit_now:
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
