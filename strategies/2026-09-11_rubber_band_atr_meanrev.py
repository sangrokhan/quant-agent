"""Strategy: The Rubber Band Strategy (ATR-band mean reversion below rolling
5-day high).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-074):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/quantitative-trading-strategies/,
visited this iteration -- the Substack article
https://quantifiedstrategies.substack.com/p/the-rubber-band-strategy has
the same name but the trading rules there are paywalled; this repo uses
the fully disclosed version of the same rule found in the "8 Quantitative
Trading Strategies" companion article), the Rubber Band strategy is a
mean-reversion play on the idea that prices snap back after being
stretched too far below their recent range:
  1. Calculate a 5-day average of (High - Low), an ATR-like measure.
  2. Calculate the highest High over the last 5 days.
  3. A band = that 5-day High minus 2.5 * the 5-day average range.
  4. If today's close is BELOW that band, go long at the close.
  5. Exit when the close is higher than YESTERDAY's high.

Source's own disclosed backtest on SPY: average gain per trade 0.66%,
win rate 77%, annual return 6.4% while invested only 14% of the time. The
Substack teaser separately reports a QQQ variant (0.30-1.1% avg gain per
trade, CAGR 14.6%, time invested 20%, MDD 27%, best of SPY/QQQ/XLP tested)
gated by a 200SMA > 50SMA long-term uptrend filter -- this repo tests both
the raw (ungated) SPY/QQQ version and an optional trend-gated variant via
the `trend_gate` parameter.

First "rolling-N-day-high minus ATR-multiple" band-touch mean-reversion
strategy in this repo -- distinct from Bollinger-Band (SMA+-std) and
Keltner-Channel (EMA+-ATR-around-a-moving-average) mean reversion already
tested, since this bands OFF the rolling HIGH (not a moving average
center), a specifically asymmetric "how far has price fallen from its
recent peak, scaled by recent range" construction.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
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
    range_window: int = 5,
    high_window: int = 5,
    band_mult: float = 2.5,
    trend_gate: bool = False,
    fast_sma: int = 50,
    slow_sma: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    avg_range = (high - low).rolling(range_window).mean()
    rolling_high = high.rolling(high_window).max()
    band = rolling_high - band_mult * avg_range

    entry = close < band
    if trend_gate:
        sma_fast = close.rolling(fast_sma).mean()
        sma_slow = close.rolling(slow_sma).mean()
        entry = entry & (sma_fast > sma_slow).fillna(False)

    prior_high = high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(close.iloc[i] > prior_high.iloc[i]) if pd.notna(prior_high.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
