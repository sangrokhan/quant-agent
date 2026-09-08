"""Strategy: Bullish Kicker candlestick reversal with RSI oversold
confluence filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-053):
Per wrtrading.com's Bullish Kicker construction rules (browser_exec
fallback -- web_search's DuckDuckGo backend returned "No results found"
for the raw query) and Bing's AI-overview aggregation of entry/exit rules
(2 sources), the Bullish Kicker is a 2-candle reversal: candle1 a strong
bearish candle closing near its low; candle2 a bullish candle that OPENS
AT OR ABOVE candle1's open (gap up, zero body overlap) and continues
rising -- distinct from plain Bullish Engulfing (already tested multiple
times in this repo, e.g. 2026-09-04-102/2026-09-08-024/2026-09-09-034)
because Kicker specifically requires the gap/no-overlap open condition,
not merely close2>open1. Source's own explicit rules: entry near the
confirming candle's close if it closes higher than the prior candle;
stop-loss just below the low of the first bearish candle (or the gap);
use RSI<30-and-turning-up as a confluence filter (source's own explicit
recommendation). First Bullish Kicker strategy in this repo.

Signal logic
------------
- Candle1 bearish: close1 < open1, and close1 near its low (close1 within
  `near_low_pct` of the candle's own range from the low).
- Candle2 bullish gap: open2 >= open1 (source's "opens at or above the
  previous open"), AND open2 > close1 (a genuine gap, no body overlap
  with candle1's close), AND close2 > open2 (candle2 itself bullish).
- RSI(14) confluence filter: RSI was below `rsi_oversold` (default 30)
  within the last `rsi_lookback` bars and has since turned up (source's
  own explicit recommendation).
- Entry (long): all candle-pattern conditions + RSI confluence true on the
  candle2 bar, entered at candle2's close.
- Exit: close falls below the low of candle1 (source's stop-loss rule),
  OR a max_hold_days time-stop.

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


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    near_low_pct: float = 0.3,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    rsi_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    candle1_bearish = close.shift(1) < open_.shift(1)
    rng1 = (high.shift(1) - low.shift(1)).replace(0, float("nan"))
    close1_near_low = ((close.shift(1) - low.shift(1)) / rng1) <= near_low_pct

    gap_up_open = open_ >= open_.shift(1)
    no_overlap = open_ > close.shift(1)
    candle2_bullish = close > open_

    rsi = _rsi(close, rsi_window)
    was_oversold = (rsi.shift(1) < rsi_oversold).rolling(rsi_lookback, min_periods=1).max().astype(bool)
    rsi_turning_up = rsi > rsi.shift(1)
    rsi_confluence = was_oversold & rsi_turning_up

    entry_signal = (
        candle1_bearish
        & close1_near_low
        & gap_up_open
        & no_overlap
        & candle2_bullish
        & rsi_confluence
    )

    stop_level_ref = low.shift(1)  # low of candle1

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    stop_level = None
    for i in range(len(close)):
        if not in_pos:
            es = entry_signal.iloc[i]
            if bool(es) if pd.notna(es) else False:
                in_pos = True
                entry_idx = i
                stop_level = stop_level_ref.iloc[i]
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            c = close.iloc[i]
            stop_hit = pd.notna(stop_level) and c < stop_level
            if stop_hit or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    near_low_pct: float = 0.3,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    rsi_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        near_low_pct=near_low_pct,
        rsi_window=rsi_window,
        rsi_oversold=rsi_oversold,
        rsi_lookback=rsi_lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
