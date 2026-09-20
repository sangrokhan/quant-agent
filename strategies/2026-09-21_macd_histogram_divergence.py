"""Strategy: MACD(12,26,9) histogram bullish divergence reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-160):
Per a Google AI-overview synthesis of MACD-divergence trading guides (SGT
Markets, StockGro, Evest -- searched this iteration via browser_exec after
web_search's DDGS/Yahoo backend hit repeated TLS RequestErrors on every
query), a MACD-histogram BULLISH DIVERGENCE occurs when price makes a lower
low over a lookback window while the MACD histogram simultaneously makes a
higher low over that same window -- i.e. downside price momentum is fading
even as price itself keeps falling, an early reversal signal. The trigger is
confirmed on the bar where the histogram itself ticks up versus the prior
bar (turning). Exit is either a bearish MACD-line/signal-line crossover or
the histogram flipping negative again (momentum failure), or a max holding
period. This is a genuinely new indicator-technique combination for this
repo: prior MACD entries here use price/signal-line CROSSOVERS or zero-line
crosses, never a histogram-vs-price DIVERGENCE construction (0 prior KB hits
for "MACD divergence" or "MACD histogram divergence").

Signal logic
------------
- Standard MACD(12,26,9): macd_line = EMA(close,12) - EMA(close,26);
  signal_line = EMA(macd_line, 9); histogram = macd_line - signal_line.
- Over a rolling `lookback` window, find the lowest price close and the
  lowest histogram value both within that window. Bullish divergence
  candidate when: today's close is within `pct_tolerance` of the window's
  lowest close (i.e. today IS (near) that lower low) AND today's histogram
  value is HIGHER than the window's minimum histogram value from an earlier
  bar (histogram not confirming the new price low).
- Entry (long): divergence candidate is true on bar t, AND histogram[t] >
  histogram[t-1] (the confirming upturn).
- Exit: macd_line crosses below signal_line (bearish crossover), OR
  histogram turns negative again, OR max_hold_days reached.
- Flat otherwise.

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


def _macd(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    lookback: int = 20,
    pct_tolerance: float = 0.01,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_line, signal_line, hist = _macd(close, fast, slow, signal)

    rolling_min_close = close.rolling(lookback).min()
    rolling_min_hist_idx = hist.rolling(lookback).apply(lambda x: x.values.argmin(), raw=False)

    # "Today is near the window's low" test.
    near_price_low = close <= rolling_min_close * (1.0 + pct_tolerance)

    # Histogram at today vs the window's minimum histogram value (earlier bar).
    rolling_min_hist = hist.rolling(lookback).min()
    hist_higher_than_window_min = hist > rolling_min_hist

    divergence_candidate = near_price_low & hist_higher_than_window_min
    hist_upturn = hist > hist.shift(1)

    entry_trigger = divergence_candidate & hist_upturn
    bearish_crossover = macd_line < signal_line
    hist_negative = hist < 0
    exit_trigger = bearish_crossover | hist_negative

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
