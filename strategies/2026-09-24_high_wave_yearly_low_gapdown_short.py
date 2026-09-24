"""Strategy: Bulkowski High Wave candlestick, short-only, filtered to the
source's own disclosed best-performing subset (near yearly low + gap
confirmation + below-50-day-SMA breakout, trading the downward-breakout
direction the source's own stats show is strongest).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/HighWave.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot usefully extract
this domain, as with every prior thepatternsite.com entry this cron
trigger).

Source's own disclosed identification rules and statistics:
    "Look for tall upper and lower shadows attached to a small body. The
    body is not a doji (the opening and closing prices must be more than
    a few pennies apart)... No price trend required."
    Theoretical performance: indecision.
    Tested performance: reversal 51% of the time (near-random -- source's
    own words: "that agrees with theory [indecision]").
    Frequency rank: 17/103 (common). Overall performance rank: 67/103
    (below mid-list).
    Source's own disclosed best individual outcome: "The best move came
    after downward breakouts in a bear market. Price dropped an average
    of 3.38%" -- i.e. among all four bull/bear x up/down combinations, the
    single strongest disclosed number is a DOWNWARD move.

Source's own "Three Trading Tidbits" (book p.412/414) disclose three
performance-boosting refinements used here:
    1. "High wave candles that appear within a third of the yearly low
       perform best" -- p.412.
    2. "High wave candles confirmed by an opening gap tend to perform
       best" -- p.414 (this strategy requires a gap DOWN at the
       confirming breakout bar, matching the disclosed downward-breakout
       edge above).
    3. "Breakouts below the 50-trading day moving average tend to
       outperform" -- p.414 (this strategy requires the breakout close
       below SMA(50), the source's own explicit numeric threshold).

This strategy trades the source's own disclosed strongest-performing
combination directly: a High Wave candle near the yearly low, confirmed by
a gap-down breakout below the pattern's low, with the breakout occurring
below the 50-day SMA -- rather than either the theoretical
"indecision/no signal" framing or a naive unfiltered reversal bet on a
near-random (51%) pattern.

First "High Wave" strategy in this repo (0 prior index hits) -- distinct
from the already-tested Long Legged Doji (source's own "See Also" section
explicitly distinguishes them: "the long legged doji has no body," while
High Wave requires a genuine non-doji body) and from Rickshaw Man
(0 prior index hits either, but a structurally different one-candle
doji-like pattern, not implemented here).

Signal logic (numeric proxy for the source's disclosed identification
guidelines + Three Trading Tidbits refinements)
------------------------------------------------------------------------
1. High Wave candle detection at bar t-1: tall upper and lower shadows
   relative to the body (shadow_min_pct of the day's range on each side)
   and a genuine non-doji body (body >= min_body_pct of the day's range).
2. Yearly-low filter (source's own disclosed best-performing subset): the
   candle's low sits within the bottom `yearly_low_third` fraction of the
   trailing `yearly_window`-day high-low range.
3. Confirmation/entry (source's own disclosed best-performing subset):
   the NEXT bar (t) opens with a gap DOWN below the High Wave candle's
   low (open[t] < low[t-1] * (1 - gap_min_pct)) AND closes below
   SMA(sma_window) evaluated at t (source's own disclosed "breakouts
   below the 50-day MA... outperform" numeric threshold) -> short entry.
4. Exit: ATR-based stop (above the High Wave candle's high) and profit
   target (`target_atr_mult` x ATR below entry), or a max_hold_days
   time-stop, whichever comes first -- same ATR-based short-exit
   mechanics already used successfully in this repo's Bearish Kicker
   (2026-09-21) and this cron trigger's Last Engulfing Bottom
   (2026-09-24-121) strategies.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    shadow_min_pct: float = 0.3,
    min_body_pct: float = 0.03,
    yearly_window: int = 252,
    yearly_low_third: float = 0.33,
    gap_min_pct: float = 0.0,
    sma_window: int = 50,
    atr_period: int = 14,
    atr_stop_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series for High Wave
    completions filtered to the source's disclosed best-performing subset
    (yearly-low proximity + gap-down confirmation + below-50-day-SMA
    breakout)."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    rng = (h - l).replace(0.0, np.nan)
    body = (c - o).abs()
    upper_shadow = h - c.where(c >= o, o)
    lower_shadow = c.where(c <= o, o) - l

    is_high_wave = (
        ((upper_shadow / rng) >= shadow_min_pct)
        & ((lower_shadow / rng) >= shadow_min_pct)
        & ((body / rng) >= min_body_pct)
    ).fillna(False)

    roll_high = h.rolling(yearly_window).max()
    roll_low = l.rolling(yearly_window).min()
    yr_range = (roll_high - roll_low).replace(0.0, np.nan)
    pos_in_range = (l - roll_low) / yr_range
    near_yearly_low = (pos_in_range <= yearly_low_third).fillna(False)

    candle_signal = (is_high_wave & near_yearly_low).fillna(False)

    sma = c.rolling(sma_window).mean()

    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None
    pending_low = None
    pending_high = None

    for i in range(n):
        if in_position:
            hit_stop = h.iloc[i] >= stop_price
            hit_target = l.iloc[i] <= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                pending_low = None
                continue
            position.iloc[i] = -1
            continue

        if i > 0 and bool(candle_signal.iloc[i - 1]):
            pending_low = l.iloc[i - 1]
            pending_high = h.iloc[i - 1]

        if pending_low is not None:
            gap_down = o.iloc[i] < pending_low * (1.0 - gap_min_pct)
            below_sma = pd.notna(sma.iloc[i]) and c.iloc[i] < sma.iloc[i]
            if gap_down and below_sma:
                entry_price = c.iloc[i]
                entry_atr = atr.iloc[i]
                if pd.notna(entry_atr) and entry_atr > 0:
                    stop_price = max(pending_high, h.iloc[i]) + atr_stop_mult * entry_atr
                    target_price = entry_price - target_atr_mult * entry_atr
                    in_position = True
                    hold_days_left = max_hold_days
                    position.iloc[i] = -1
                pending_low = None
                continue
            else:
                # only give the confirmation window one bar
                pending_low = None

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Short
    positions (-1) profit when price falls."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
