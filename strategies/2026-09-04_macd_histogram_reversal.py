"""Strategy: MACD Histogram Momentum Reversal (mean-reversion variant).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-100):
Per quantifiedstrategies.com's "Core MACD Histogram Strategies" section
(non-paywalled): a "Histogram Momentum Reversal" signal fires when the MACD
histogram (MACD line - signal line) is BELOW the zero line (bearish
momentum territory) and turns from falling to rising (an inflection --
decreasing bearish momentum), signaling a potential bottom/reversal-up
worth a long entry. The source's own free exit rule: exit on the first day
the close is higher than the previous day's close (a very fast,
mean-reversion-style exit -- take the first sign of upward price
confirmation and get out). This is a genuine mean-reversion use of the
MACD histogram, distinct from every prior MACD-family strategy in this repo
(all of which use the histogram/line as a TREND/momentum-continuation gate
or crossover, not a reversal-at-extreme signal).

Signal logic
------------
- MACD line = EMA(fast_window, close) - EMA(slow_window, close)
- Signal line = EMA(signal_window, MACD line)
- Histogram = MACD line - Signal line
- Entry: histogram[t] < 0 (below zero line) AND histogram[t] > histogram[t-1]
  AND histogram[t-1] <= histogram[t-2] (histogram was falling or flat, now
  turned up -- the falling-to-rising inflection).
- Exit: close[t] > close[t-1] (first day price closes higher than the
  prior day, per source's stated exit rule) -- checked starting the day
  AFTER entry (can't exit same-day as entry).
- No trend filter (source's rule is presented as effective on its own,
  unlike most other strategies in this repo which add a 200d SMA gate) --
  tested both with and without an optional 200d trend filter via the
  `require_uptrend` parameter for robustness.

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


def _histogram(close: pd.Series, fast_window: int, slow_window: int, signal_window: int) -> pd.Series:
    macd_line = close.ewm(span=fast_window, adjust=False).mean() - close.ewm(span=slow_window, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
    trend_window: int = 200,
    require_uptrend: bool = False,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hist = _histogram(close, fast_window, slow_window, signal_window)
    below_zero = hist < 0
    turning_up = (hist > hist.shift(1)) & (hist.shift(1) <= hist.shift(2))
    entry = below_zero & turning_up

    if require_uptrend:
        trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
        entry = entry & (close > trend_sma).fillna(False)

    price_up = close > close.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= 1 and (bool(price_up.iloc[i]) or held >= max_hold_days):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i].item() if hasattr(entry.iloc[i], "item") else entry.iloc[i]):
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
