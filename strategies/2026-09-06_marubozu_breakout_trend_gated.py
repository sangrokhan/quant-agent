"""Strategy: Bullish Marubozu breakout confirmation, trend-gated, long-only.

Hypothesis (see knowledge_base id 2026-09-06-146):
Per Trading Setups Review's Marubozu Candlestick Pattern Trading Guide
(https://www.tradingsetupsreview.com/marubozu-candlestick-pattern-trading-guide/):
a Marubozu candle has minimal wicks -- "For a Marubozu, we want the candle
body to take up at least 95% of the candlestick [range]" -- and represents
"urgency of market players... when the market shows urgency in a direction,
it prompts strong expectations... for instance, when we see a bullish
Marubozu, we expect prices to continue rising in the short-term." Per the
Google-search-surfaced TrendSpider snippet's stated entry tactic: "Breakout
Entry: Enter when the price breaks above a bullish Marubozu high."

Operationalized as a trend-continuation strategy: a bullish Marubozu
(body >= marubozu_body_pct of the day's true range, close>open) forming
within a confirmed uptrend (close > SMA(trend_window)) marks a
high-conviction bar; entry triggers on the NEXT bar's close breaking above
that Marubozu's high (the TrendSpider-cited breakout tactic, avoiding a
same-bar chase entry). First candlestick-pattern strategy in this repo using
a body-to-range-ratio definition rather than open/close relative-position
comparisons (distinct from Bullish Engulfing 2026-09-04-102 and Three White
Soldiers 2026-09-06-132).

Signal logic
------------
- Marubozu body ratio: (close-open)/(high-low) for a bullish candle; must be
  >= marubozu_body_pct (default 0.95, per source's "at least 95%").
- Trend filter: close > SMA(trend_window) (default 200) at the Marubozu bar.
- Entry: on the first subsequent bar whose close breaks above the qualifying
  Marubozu bar's high, within breakout_expiry_bars of it forming (if the
  breakout doesn't happen within that window, the setup expires).
- Exit: close crosses back below the entry-triggering Marubozu's own low
  (failure/stop), OR close crosses below SMA(trend_window) (trend break),
  OR a max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    marubozu_body_pct: float = 0.95,
    trend_window: int = 200,
    breakout_expiry_bars: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    close = df["close"]
    n = len(close)

    true_range = (high - low).replace(0.0, np.nan)
    body_ratio = (close - open_) / true_range
    is_bullish = close > open_
    is_marubozu = is_bullish & (body_ratio >= marubozu_body_pct)

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma
    qualifying = (is_marubozu & uptrend).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_low = np.nan
    pending_bar = None  # index of a qualifying Marubozu bar awaiting breakout

    for i in range(n):
        if in_position:
            held = i - entry_idx
            trend_break = not bool(uptrend.iloc[i])
            stop_hit = (not np.isnan(stop_low)) and (close.iloc[i] < stop_low)
            if trend_break or stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_low = np.nan
                pending_bar = None
                continue
            position.iloc[i] = 1
        else:
            # check if a pending setup breaks out this bar
            if pending_bar is not None:
                bars_since = i - pending_bar
                if bars_since > breakout_expiry_bars:
                    pending_bar = None
                elif close.iloc[i] > high.iloc[pending_bar]:
                    in_position = True
                    entry_idx = i
                    stop_low = low.iloc[pending_bar]
                    position.iloc[i] = 1
                    pending_bar = None
                    continue
            if pending_bar is None and bool(qualifying.iloc[i]):
                pending_bar = i
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
