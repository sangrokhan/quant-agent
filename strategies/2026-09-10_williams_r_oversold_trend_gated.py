"""Strategy: Williams %R deep-oversold mean reversion, gated by a long-term
trend filter (targeting the crypto asset class where the ungated version
failed).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-118):
Per a Google AI-overview synthesis of QuantifiedStrategies.com's Williams %R
article (https://www.quantifiedstrategies.com/williams-r-strategy/, via
browser_exec fallback google.com SERP -- web_search DDGS backend query for
this topic returned no usable snippet content): the classic 2-period
Williams %R deep-oversold rule (%R < -90/-95 entry) works well on equity
indices but the source's own "Crypto Backtest Considerations" section notes
that on crypto assets the ultra-short 2-period lookback generates "constant
whipsaws" because crypto frequently spikes to its own daily high/low, and
that "applying a higher-timeframe trend filter (such as the 200-period
Moving Average) dramatically improves win rates by taking only long signals
when the crypto asset is in an overarching bull trend."

This repo's existing Williams %R oversold entry (2026-09-04-030, id
strategies/2026-09-04_williams_r_oversold.py) used the exact -90/-30
entry/exit thresholds with NO trend filter and was accepted for QQQ/SPY but
REJECTED for crypto. A separate existing strategy (2026-09-08-115) tested a
50-SMA trend filter but with a completely different -80/-20 cross-back
entry mechanic (not the deep -90 threshold-breach mechanic). This iteration
directly tests the source's own disclosed fix for the specific asset class
that failed before: same deep-oversold -90/-95 entry mechanic as
2026-09-04-030, but gated by close > SMA(trend_window) with trend_window
defaulting to 200 (source's explicit crypto recommendation), and exit
threshold loosened to the source's suggested "median" -50 (vs the original
-30) to reduce whipsaw re-entries. Distinct from both prior Williams %R
entries via this specific entry-mechanic + trend-filter-window + exit-level
combination.

Signal logic
------------
- Williams %R(williams_window) = -100 * (rolling_high(high, window) -
  close) / (rolling_high(high, window) - rolling_low(low, window)).
- Trend filter: close > SMA(trend_window) (long-only "in an overarching
  bull trend" per source).
- Entry (long): close's Williams %R < oversold_threshold (source: -90 or
  -95) AND trend filter is true.
- Exit: close > prior day's high (recovery breakout) OR Williams %R >
  exit_threshold (source's "median threshold like -50 or -30"; default
  here -50) OR the trend filter breaks (close <= SMA(trend_window)).
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _williams_r(df: pd.DataFrame, williams_window: int) -> pd.Series:
    high_max = df["high"].rolling(williams_window).max()
    low_min = df["low"].rolling(williams_window).min()
    denom = (high_max - low_min).replace(0.0, pd.NA)
    return -100.0 * (high_max - df["close"]) / denom


def generate_signals(
    price_df: pd.DataFrame,
    williams_window: int = 2,
    oversold_threshold: float = -90.0,
    exit_threshold: float = -50.0,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    williams_r = _williams_r(df, williams_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma).fillna(False)

    entry = (williams_r < oversold_threshold).fillna(False) & uptrend
    prior_high = high.shift(1)
    exit_recover = (
        (close > prior_high)
        | (williams_r > exit_threshold)
        | (~uptrend)
    )
    exit_recover = exit_recover.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_recover.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
