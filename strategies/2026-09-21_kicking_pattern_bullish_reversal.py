"""Strategy: Bullish Kicking candlestick reversal pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-273):
Per the standard/public-domain candlestick-pattern definition (Nison/
Investopedia-style classic 2-candle reversal, this repo already has several
other 2-candle patterns from the same reference family -- Railroad Tracks,
Belt Hold, Counterattack -- all 0 prior "Kicking Pattern" KB hits confirm
this is genuinely new), the "Kicking" pattern is one of the strongest
classic reversal signals: bar1 is a long bearish MARUBOZU (a candle with
essentially no upper/lower shadow, real body close to the full high-low
range, i.e. open ~= high and close ~= low for a bearish marubozu), bar2
GAPS UP so that its entire range (including shadows) sits above bar1's
entire range, and bar2 is itself a long bullish marubozu (open ~= low,
close ~= high). The un-shadowed "marubozu" requirement on BOTH candles plus
the full-range (not just body) gap is what distinguishes Kicking from the
weaker, much more common "opposite-color engulfing with a body gap" family
already covered by this repo's Separating Lines / Counterattack Line
entries (those only require body-level relationships, not marubozu
shadow-free bodies + full-range gaps). The classic interpretation: a
sudden aggressive reversal in sentiment (violent whipsaw from one extreme
sentiment candle to the opposite) is a strong continuation-of-the-new-
direction signal.

Signal logic
------------
- Bar1 (t-1): bearish marubozu -- close[t-1] < open[t-1], and both the
  upper shadow (open[t-1] - high[t-1], i.e. how far open is below the
  high) and lower shadow (low[t-1] vs close[t-1]) are small relative to
  the bar's own range (<= shadow_tolerance * range).
- Bar2 (t): bullish marubozu -- close[t] > open[t], with small upper/lower
  shadows by the same shadow_tolerance test.
- Full-range gap: bar2's entire range sits above bar1's entire range,
  i.e. low[t] > high[t-1] (a genuine gap, not just a body-level gap).
- Entry: long at the close of bar2 itself (the pattern's own last bar is
  the actionable signal bar, per the classic "kicking" reversal
  definition -- no separate confirmation-breakout bar required, unlike
  Railroad Tracks, since the marubozu + full-range-gap combination is
  already a strict enough filter).
- Exit: close falls below bar2's own low (structural invalidation of the
  new up-move) OR max_hold_days reached, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
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
    shadow_tolerance: float = 0.1,
    max_hold_days: int = 12,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    rng = (high - low).replace(0.0, float("nan"))

    # marubozu tests: shadows small relative to bar's own range
    bearish_upper_shadow = (high - open_) / rng
    bearish_lower_shadow = (close - low) / rng
    bearish_marubozu = (
        (close < open_)
        & (bearish_upper_shadow <= shadow_tolerance)
        & (bearish_lower_shadow <= shadow_tolerance)
    )

    bullish_upper_shadow = (high - close) / rng
    bullish_lower_shadow = (open_ - low) / rng
    bullish_marubozu = (
        (close > open_)
        & (bullish_upper_shadow <= shadow_tolerance)
        & (bullish_lower_shadow <= shadow_tolerance)
    )

    bar1_bearish_marubozu = bearish_marubozu.shift(1)
    full_range_gap_up = low > high.shift(1)

    entry_signal = (bar1_bearish_marubozu & bullish_marubozu & full_range_gap_up).fillna(False)
    structural_stop_level = low.where(entry_signal).ffill()

    position = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    hold_bars = 0
    stop_level = None
    for i in range(n):
        if in_pos:
            hold_bars += 1
            if close.iloc[i] < stop_level or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
                stop_level = None
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_bars = 0
                stop_level = low.iloc[i]
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    shadow_tolerance: float = 0.1,
    max_hold_days: int = 12,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, shadow_tolerance=shadow_tolerance, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
