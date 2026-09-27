"""Strategy: Long-Legged Doji at Bollinger Band Extreme -> Mean-Reversion to Middle Band.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-085):
Per LuxAlgo's "5 Long-Legged Doji Entry Strategies"
(https://www.luxalgo.com/blog/5-long-legged-doji-entry-strategies/, read via
browser_exec fallback -- web_search for the initial "quantitativo new post"
angle came back with unrelated results this iteration), Strategy #3
("Doji at a Bollinger Band extreme"): a long-legged doji (small real body
relative to its high-low range, long shadows both sides) whose shadow
reaches beyond a Bollinger Band (20-period SMA, 2 std) signals a stretched,
rejected move. The source's own disclosed rule: entry trigger is a
confirmation close back TOWARD the middle band (i.e., the day after the
doji, price closes moving back inside/toward the mean) with "no fresh band
expansion in the direction of the prior move"; target is the middle band
(the 20-SMA itself, used here as the natural exit level for a mean-reversion
trade rather than a fixed take-profit); stop beyond the extreme shadow.

This combines the doji body-definition (per Bulkowski/LuxAlgo's Library
doji entry: real body must be a small fraction of the day's high-low range)
with a Bollinger Band extreme filter and a mean-reversion-to-middle-band
exit -- distinct from every other BB mean-reversion strategy already in
this repo (e.g. 2026-09-04 bb_pctb_meanrev_connors, bb_rsi_confirmation_meanrev)
because the ENTRY TRIGGER here is a specific single-candle doji pattern at
the band extreme (not a plain %b/close-below-band threshold), and distinct
from every candlestick-pattern strategy already tested (doji patterns have
0 prior standalone KB hits; the closest prior entry, combined_candlestick_
meanrev 2026-09-21-269, uses five different bearish-named reversal patterns,
none of which is a doji).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _bollinger(close: pd.Series, window: int, num_std: float):
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    doji_body_frac: float = 0.1,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0, 1} short/flat/long position series.

    Doji day (day t-1): |close-open| <= doji_body_frac * (high-low), and
    shadow reaches beyond a Bollinger Band computed as of that day.
    Confirmation day (day t): close moves back toward the middle band
    relative to the doji day's close (i.e. direction of the mean-reversion
    trade), entered at that confirmation day's close. Exit when close
    reaches/crosses the middle band, or max_hold_days time-stop.
    """
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    mid, upper, lower = _bollinger(close, bb_window, bb_std)

    body = (close - open_).abs()
    rng = (high - low).replace(0, pd.NA)
    is_doji = (body <= doji_body_frac * rng).fillna(False)

    shadow_above_upper = high > upper
    shadow_below_lower = low < lower

    doji_upper = is_doji & shadow_above_upper.fillna(False)
    doji_lower = is_doji & shadow_below_lower.fillna(False)

    # Confirmation day: shift doji flags forward by 1 day.
    confirm_short = doji_upper.shift(1).fillna(False) & (close < close.shift(1))
    confirm_long = doji_lower.shift(1).fillna(False) & (close > close.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    direction = 0
    entry_idx = 0
    for i in range(len(close)):
        if in_pos:
            held = i - entry_idx
            reached_mid = (
                (direction == 1 and close.iloc[i] >= mid.iloc[i])
                or (direction == -1 and close.iloc[i] <= mid.iloc[i])
            ) if pd.notna(mid.iloc[i]) else False
            if bool(reached_mid) or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = direction
        else:
            if bool(confirm_long.iloc[i]):
                in_pos = True
                direction = 1
                entry_idx = i
                position.iloc[i] = 1
            elif bool(confirm_short.iloc[i]):
                in_pos = True
                direction = -1
                entry_idx = i
                position.iloc[i] = -1
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
