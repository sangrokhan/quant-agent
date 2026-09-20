"""Strategy: VSA (Volume Spread Analysis) "No Supply" bar within an
established uptrend -- bullish continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-162):
Per a Google AI-overview synthesis of Volume Spread Analysis guides
(LuxAlgo, DXP Analytics, Kotak Neo -- searched this iteration via
browser_exec after web_search's DDGS/Yahoo backend TLS-erroring on every
query), a "No Supply" bar is a down bar (close below the prior bar's low)
with a NARROW spread (price range) AND volume LOWER than each of the
preceding 2 bars, occurring within an established uptrend. The VSA
interpretation: price pulled back on a down bar, but the unusually LOW
volume means genuine sellers weren't actually present -- supply has "dried
up" -- so the pullback is a low-conviction pause rather than a trend
reversal, and price should resume its prior uptrend. This is the inverse
construction of every prior volume-confirmation strategy in this repo (which
all require HIGH volume to CONFIRM a breakout); here LOW volume on a
pullback bar is itself the bullish signal, requiring an existing-uptrend
context per the sources' own caveat that "a no-supply bar means nothing
without an established trend to confirm it against." First VSA no-supply/
no-demand strategy in this repo (0 prior KB hits).

Signal logic
------------
- Established uptrend context: close > SMA(trend_window) AND
  SMA(trend_window) is itself rising over the last `slope_lookback` bars.
- Down bar: close < low.shift(1) (VSA's "down bar" close-vs-prior-low test).
- Narrow spread: (high - low) <= narrow_spread_pctile-th percentile of the
  trailing `spread_window`-bar range distribution.
- Low volume: volume < volume.shift(1) AND volume < volume.shift(2) (lower
  than each of the preceding 2 bars).
- Entry (long): all of the above true on bar t (i.e. a confirmed No-Supply
  bar within an uptrend) -> enter at t+1 (next bar's open proxy via
  position.shift(1) already built into generate_returns).
- Exit: close crosses below SMA(trend_window) (trend context broken) OR
  max_hold_days reached.

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
    trend_window: int = 50,
    slope_lookback: int = 10,
    narrow_spread_pctile: float = 0.3,
    spread_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    sma_trend = close.rolling(trend_window).mean()
    uptrend_context = (close > sma_trend) & (sma_trend > sma_trend.shift(slope_lookback))

    down_bar = close < low.shift(1)

    spread = high - low
    spread_threshold = spread.rolling(spread_window).quantile(narrow_spread_pctile)
    narrow_spread = spread <= spread_threshold

    low_volume = (volume < volume.shift(1)) & (volume < volume.shift(2))

    no_supply_bar = uptrend_context & down_bar & narrow_spread & low_volume

    exit_trend_break = close < sma_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(no_supply_bar.iloc[i]):
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
