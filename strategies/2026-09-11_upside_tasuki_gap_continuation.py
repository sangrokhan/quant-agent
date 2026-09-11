"""Strategy: Upside Tasuki Gap bullish continuation, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-123):
Source: https://enlightenedstocktrading.com/upside-tasuki-gap-candlestick-pattern/
Upside Tasuki Gap is a 3-candle bullish CONTINUATION pattern that appears
during an existing uptrend: candle1 is a strong bullish candle confirming
the uptrend; candle2 is another bullish candle that gaps up, trading
entirely above candle1's high-low range; candle3 is a bearish candle that
opens within candle2's body and closes back down inside the candle1-candle2
gap, but does NOT fully close the gap (candle3's close stays above
candle1's high) -- signalling that despite a brief pullback attempt,
buyers remain in control and the up-move is likely to continue. Per the
source's own risk-management guidance: enter after candle3 closes (gap
still open), stop below candle3's low.

First Upside Tasuki Gap strategy in this repo (zero prior hits in
strategies_index.jsonl) -- distinct from the previously-tested Stick
Sandwich (2026-09-09-036, a bearish-in-downtrend 3-candle REVERSAL
pattern) and from all other prior gap-based strategies (Unfilled Gap RSI,
ATR Gap Down) via its specific 3-candle bullish-continuation-with-partial-
gap-fill structure.

Mechanical rule implemented
----------------------------
- candle1: bullish (close1 > open1), body1 = close1 - open1 >= min_body_pct
  * (high1 - low1) (a "strong" bullish candle, not a doji).
- candle2: bullish (close2 > open2) AND low2 > high1 (fully gaps up above
  candle1's entire range -- the disclosed "trading completely above the
  first candle's range").
- candle3: bearish (close3 < open3), opens within candle2's body
  (open2 <= open3 <= close2), closes back down into the gap zone
  (close3 < low2) but does NOT fully close it (close3 > high1).
- Trend context: close1 > SMA(trend_window) (source: "works best in
  strong uptrends").
- Entry (long): the day candle3 completes (all three conditions above
  hold, evaluated at candle3's close -- no look-ahead, since we act on
  today's close being candle3, holding overnight into tomorrow).
- Exit: close falls below candle3's low (stop, per source's own stop-loss
  guidance), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: {0,1})
    generate_returns(price_df, **params) -> pd.Series
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
    trend_window: int = 50,
    min_body_pct: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    open1, close1, high1, low1 = open_.shift(2), close.shift(2), high.shift(2), low.shift(2)
    open2, close2, low2 = open_.shift(1), close.shift(1), low.shift(1)
    open3, close3, low3 = open_, close, low

    body1 = (close1 - open1).abs()
    range1 = (high1 - low1).replace(0, pd.NA)
    strong_c1 = (close1 > open1) & ((body1 / range1) >= min_body_pct)

    gap_up_c2 = (close2 > open2) & (low2 > high1)

    bearish_c3 = close3 < open3
    opens_in_body2 = (open3 >= open2.where(open2 <= close2, close2)) & (open3 <= open2.where(open2 >= close2, close2))
    closes_into_gap = (close3 < low2) & (close3 > high1)

    trend_ok = close1 > close1.rolling(trend_window).mean()

    entry = strong_c1.fillna(False) & gap_up_c2.fillna(False) & bearish_c3.fillna(False) \
        & opens_in_body2.fillna(False) & closes_into_gap.fillna(False) & trend_ok.fillna(False)

    stop_level = low3  # candle3's low, locked in on entry day

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_stop = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(close.iloc[i] < entry_stop) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_stop = float(stop_level.iloc[i])
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
