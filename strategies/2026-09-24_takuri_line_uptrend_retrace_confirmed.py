"""Strategy: Bulkowski Takuri Line candlestick, bullish reversal (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/TakuriLine.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend returns unrelated
results for this domain, confirmed again this iteration).

Source's own disclosed identification rules and statistics:
    "A small bodied candle with a lower shadow at least three times the
    height of the body and little or no upper shadow." Theoretical
    performance: Bullish reversal. Tested performance: Bullish reversal
    66% of the time. Overall performance rank: 47/103 (mid-pack -- "even
    though price may reverse the downward price trend often, price does
    not trend far after that").

This repo already tested and REJECTED a generic Hammer strategy
(2026-09-06-147, wick_to_body_ratio=2.0, standalone downtrend context,
decisive full-sample failure, pass_fraction 0.088). The Takuri Line is
NOT simply a re-run of that: it has (1) a STRICTER numeric shadow ratio
(source's own disclosed >=3x, vs the generic Hammer's commonly-used 2x),
and (2) the source's own disclosed "Three Trading Tidbits" prescribe a
DIFFERENT, stronger context than the rejected Hammer's plain downtrend
gate: "Look for the Takuri line as part of a downward retracement in an
up trend" (book p.724) plus "To confirm a Takuri line, wait for price to
close higher the next day" (p.724-725) -- an explicit next-day
confirmation bar the rejected Hammer strategy never required. This
strategy implements exactly that stronger, source-preferred combination
(uptrend context + tighter 3x wick ratio + confirmation bar), following
the same successful pattern as this repo's Above the Stomach strategy
(2026-09-24), which used the source's own strongest disclosed context
rather than its generic framing.

First Takuri Line strategy in this repo (0 prior KB index hits).

Signal logic
------------
1. Longer-term uptrend filter: close > SMA(uptrend_window) (source's own
   preferred context: "downward retracement in an up trend").
2. Short-term retracement filter: close[t-1] < close[t-1-retrace_lookback]
   (a genuine local pullback leading into the pattern bar).
3. Pattern bar (t-1) anatomy: small body (|close-open| <= max_body_pct of
   the bar's own high-low range), long lower shadow (lower_shadow >=
   wick_to_body_ratio x body, using max(body, min_body_epsilon) to avoid
   division-by-zero for near-doji bars), minimal upper shadow (upper
   shadow <= body).
4. Confirmation (source's own disclosed rule): today's (t) close is
   higher than the pattern bar's (t-1) close.
5. Entry: at the confirmation bar's (t) own close.
6. Exit: close falls below its own SMA(exit_sma_window) (retracement/
   trend-continuation failure) OR a max_hold_days time-stop, whichever
   comes first -- same exit convention as this repo's other
   single-pattern-trigger candlestick strategies (e.g. Above the Stomach,
   Homing Pigeon).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    uptrend_window: int = 100,
    retrace_lookback: int = 5,
    wick_to_body_ratio: float = 3.0,
    max_body_pct: float = 0.35,
    exit_sma_window: int = 15,
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

    uptrend_sma = close.rolling(uptrend_window).mean()
    uptrend_filter = close > uptrend_sma
    retrace_filter = close.shift(2) < close.shift(2 + retrace_lookback)

    # Pattern bar is t-1 (bar before today's confirmation bar).
    p_open = open_.shift(1)
    p_close = close.shift(1)
    p_high = high.shift(1)
    p_low = low.shift(1)

    body = (p_close - p_open).abs()
    rng = (p_high - p_low).replace(0, pd.NA)
    body_pct = body / rng

    upper_shadow = p_high - p_open.where(p_close >= p_open, p_close)
    lower_shadow = p_open.where(p_close >= p_open, p_close) - p_low

    body_eps = body.clip(lower=1e-9)
    small_body = body_pct <= max_body_pct
    long_lower_shadow = lower_shadow >= wick_to_body_ratio * body_eps
    minimal_upper_shadow = upper_shadow <= body_eps

    pattern_bar = (
        small_body.fillna(False)
        & long_lower_shadow.fillna(False)
        & minimal_upper_shadow.fillna(False)
        & uptrend_filter.shift(1).fillna(False)
        & retrace_filter.fillna(False)
    )

    confirmation = close > p_close

    pattern_confirmed = (pattern_bar & confirmation).fillna(False)

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
