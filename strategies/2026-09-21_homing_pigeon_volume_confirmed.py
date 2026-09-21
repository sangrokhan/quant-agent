"""Strategy: Bullish Homing Pigeon candlestick pattern with volume-surge
confirmation filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-21-221):
Per QuantifiedStrategies.com's "Bullish Homing Pigeon Candlestick Pattern:
Backtest" (https://www.quantifiedstrategies.com/bullish-homing-pigeon-candlestick-pattern/,
read via browser_exec this iteration), the Bullish Homing Pigeon is a
2-candle bullish reversal pattern that occurs in a downtrend:

    - Bar1 (t-1): a bearish candle (close < open), continuing the downtrend.
    - Bar2 (t): ALSO a bearish candle (close < open), but its ENTIRE
      high-low range is fully confined within bar1's high-low range
      (a smaller, contained bearish candle -- structurally identical to a
      Bullish Harami except bar2 is bearish here, not bullish).
    - Source's own explicit distinction: "the difference [vs Bullish
      Harami] lies in that the second candle of a bullish harami is
      positive, while it's bearish for a bullish homing pigeon."
    - Source's own disclosed enhancement filter (their own "filters and
      conditions that have worked very well for us"): a VOLUME filter
      requiring bar2's volume to be meaningfully HIGHER than bar1's volume
      ("demand that the second candle forms with much higher volume than
      the first candle... would show that the bullish move was more
      significant than the preceding bearish move" -- despite bar2 being
      bearish in price, elevated volume on the contained/arrested bar
      signals absorption/support forming).

This is a genuinely new pattern for this repo (0 prior "homing pigeon"
hits in strategies_index.jsonl) -- distinct from Bullish Harami (bar2 must
be BULLISH, already tested 2026-09-06-150) and Inside Bar / NR7 (no
downtrend-context or bearish-bar1 requirement).

Signal logic (long-only implementation)
----------------------------------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback] (pattern must
  occur after a genuine downswing).
- Bar1 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t) bearish: close[t] < open[t].
- Containment: high[t] <= high[t-1] AND low[t] >= low[t-1] (bar2's entire
  range confined within bar1's range).
- Volume confirmation (source's own disclosed enhancement): volume[t] >=
  vol_mult * volume[t-1] (bar2 traded on meaningfully higher volume than
  bar1, despite being a smaller/contained bearish candle -- absorption
  signal).
- Entry: at bar2's own close once the pattern is confirmed (source treats
  the pattern as fully formed at bar2's close, same as Bullish Harami's
  own confirmed-at-close convention already used elsewhere in this repo).
- Exit: close falls below its own SMA(exit_sma_window) (trend
  invalidation) OR max_hold_days reached, whichever comes first (same
  exit convention as this repo's other single-pattern-trigger candlestick
  strategies e.g. Piercing Pattern 2026-09-21-166).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  {0,1} position series
    generate_returns(price_df, **params) -> pd.Series  daily strategy returns
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
    trend_lookback: int = 10,
    vol_mult: float = 1.2,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=idx)

    downtrend = close.shift(2) < close.shift(2 + trend_lookback)
    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_bearish = close < open_
    contained = (high <= high.shift(1)) & (low >= low.shift(1))
    vol_confirm = volume >= vol_mult * volume.shift(1)

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_bearish.fillna(False)
        & contained.fillna(False)
        & vol_confirm.fillna(False)
    )

    exit_sma = close.rolling(exit_sma_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_days = i - entry_i
            trend_exit = close.iloc[i] < exit_sma.iloc[i] if pd.notna(exit_sma.iloc[i]) else False
            if trend_exit or hold_days >= max_hold_days:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(pattern_confirmed.iloc[i]):
                in_position = True
                entry_i = i
                position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
