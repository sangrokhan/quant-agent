"""Strategy: Mark Minervini's Trend Template (7 single-symbol criteria).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per ChartMill.com's step-by-step guide (fully disclosed, no paywall):
https://www.chartmill.com/documentation/stock-screener/technical-analysis-trading-strategies/496-Mark-Minervini-Trend-Template-A-Step-by-Step-Guide-for-Beginners

Mark Minervini's "Trend Template" is an 8-criteria checklist for
identifying Stage 2 uptrend stocks:
  1. Price > 150-day MA
  2. Price > 200-day MA
  3. 150-day MA trending upward (rising slope)
  4. 200-day MA trending upward (rising slope)
  5. 50-day MA > 150-day MA
  6. 50-day MA > 200-day MA
  7. Price >= 30% above its 52-week low
  8. Price within 25% of its 52-week high
  (9th, informally: Relative Strength rating >= 70, vs. ALL other stocks in
  a cross-sectional universe -- explicitly FEASIBILITY-BLOCKED in this repo,
  same reasoning already documented in 2026-09-11-102: this repo's
  data/loaders.py exposes single-symbol OHLCV only, no cross-sectional
  multi-asset ranking architecture. Dropped from this test.)

This iteration tests the 7 single-symbol-computable criteria (1-2, 3-4
implemented via a rolling-slope check over a `slope_lookback` window, 5-6,
7-8) ALL simultaneously true as the long-entry gate; exit when ANY criterion
breaks (a stricter "Stage 2 confirmed" all-or-nothing filter, in the spirit
of Minervini's own "all criteria must be met" screening philosophy) or a
max_hold_days time-stop backstop.

Distinct from the already-tested VCP (Volatility Contraction Pattern,
2026-09-06-111, rejected) -- that strategy targets Minervini's specific
*entry pattern* (successive shallower pullbacks + volume dry-up + breakout);
this strategy targets his *regime-qualification checklist* (the Trend
Template), a different, coarser filter that Minervini himself describes as
a prerequisite screen BEFORE looking for a VCP or other entry pattern.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    ma50: int = 50,
    ma150: int = 150,
    ma200: int = 200,
    slope_lookback: int = 20,
    low_pct_above: float = 0.30,
    high_pct_within: float = 0.25,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma50 = close.rolling(ma50).mean()
    sma150 = close.rolling(ma150).mean()
    sma200 = close.rolling(ma200).mean()

    sma150_rising = sma150 > sma150.shift(slope_lookback)
    sma200_rising = sma200 > sma200.shift(slope_lookback)

    low_52w = close.rolling(252, min_periods=100).min()
    high_52w = close.rolling(252, min_periods=100).max()

    crit1 = close > sma150
    crit2 = close > sma200
    crit3 = sma150_rising
    crit4 = sma200_rising
    crit5 = sma50 > sma150
    crit6 = sma50 > sma200
    crit7 = close >= low_52w * (1.0 + low_pct_above)
    crit8 = close <= high_52w * (1.0 + high_pct_within)

    all_criteria = (
        crit1 & crit2 & crit3 & crit4 & crit5 & crit6 & crit7 & crit8
    ).fillna(False)

    entry = all_criteria & ~all_criteria.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = (not bool(all_criteria.iloc[i])) or held >= max_hold_days
            if exit_now:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(all_criteria.iloc[i]):
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
