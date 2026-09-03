"""Strategy: Elder's Triple Screen (weekly MACD-histogram trend + daily
Stochastic oversold pullback entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-044):
Per a Google AI-overview synthesis of Dr. Alexander Elder's Triple Screen
Trading System: Screen 1 (weekly MACD-Histogram slope) determines the
major trend direction; Screen 2 (daily Stochastic oscillator) identifies
pullbacks against that trend -- in a weekly uptrend, wait for the daily
Stochastic %K to dip below an oversold threshold (30) then recover, as the
buy trigger. This is the first genuinely multi-timeframe (weekly trend +
daily entry) strategy tested in this repo.

Implementation notes
---------------------
- Weekly trend: resample daily close to weekly (W-FRI) bars, compute
  MACD(12,26,9) histogram (MACD line - signal line) on the WEEKLY series,
  require histogram > 0 AND rising (histogram > histogram.shift(1)) as the
  "weekly tide" bullish condition, then forward-fill this weekly boolean
  back onto the daily index (source's own instruction: ignore short-term
  counter-trend signals contrary to the weekly tide).
- Daily oscillator: standard %K/%D stochastic (k_window, d_window=3),
  entry trigger = %K crosses back above the oversold threshold after
  having been below it (recovery from oversold, avoids buying into a
  still-falling knife), matching the zone-gated convention already used in
  strategies/2026-09-04_stoch_oversold_crossover.py.
- Entry (long): weekly tide bullish AND daily %K crosses above
  oversold_threshold (recovery cross). Exit: weekly tide turns bearish
  (histogram <= 0 or falling) OR daily %K crosses back below the
  overbought complement is NOT used here (source's Screen-3 stop-order
  entry mechanics are simplified to a same-bar market entry, consistent
  with every other long-only strategy in this repo) -- exit purely on the
  weekly trend breaking, letting winners run within the weekly uptrend.

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


def _weekly_macd_hist_bullish(df: pd.DataFrame) -> pd.Series:
    """Weekly MACD(12,26,9) histogram > 0 and rising, forward-filled to daily."""
    weekly_close = df["close"].resample("W-FRI").last().dropna()
    ema12 = weekly_close.ewm(span=12, adjust=False).mean()
    ema26 = weekly_close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal

    weekly_bullish = (hist > 0) & (hist > hist.shift(1))
    # Forward-fill weekly signal onto the daily index (as-of the most
    # recently completed weekly bar) -- reindex with ffill to avoid
    # lookahead (weekly bar is only "known" once it closes).
    daily_bullish = weekly_bullish.reindex(df.index, method="ffill").fillna(False)
    return daily_bullish


def _stochastic(df: pd.DataFrame, k_window: int, d_window: int = 3) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(k_window).min()
    high_max = df["high"].rolling(k_window).max()
    rng = (high_max - low_min).replace(0, pd.NA)
    percent_k = 100 * (df["close"] - low_min) / rng
    percent_k = percent_k.fillna(50.0)
    percent_d = percent_k.rolling(d_window).mean()
    return percent_k, percent_d


def generate_signals(
    price_df: pd.DataFrame,
    k_window: int = 14,
    oversold_threshold: float = 30.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    weekly_bullish = _weekly_macd_hist_bullish(df)
    percent_k, _ = _stochastic(df, k_window)

    was_oversold = percent_k.shift(1) < oversold_threshold
    recovery_cross = (percent_k >= oversold_threshold) & was_oversold.fillna(False)

    entry = recovery_cross & weekly_bullish

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if not bool(weekly_bullish.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
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
