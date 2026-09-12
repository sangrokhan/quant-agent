"""Strategy: Cost-aware deadband EMA-crossover momentum (BTC/USDT, ETH/USDT).

Source: Bysik & Slepaczuk, "Machine Learning-Based Bitcoin Trading Under
Transaction Costs: Evidence From Walk-Forward Forecasting" (arXiv:2606.00060,
May 2026), read this iteration via browser_exec (web_search DDGS backend
used for discovery, browser_exec used to read the abstract directly since
full ML reproduction -- XGBoost/LSTM/iTransformer walk-forward forecasting
-- is out of scope for a single research-loop iteration). Key finding:
"naive sign-based strategies fail once transaction costs of ten basis
points are imposed. A cost-aware execution filter, which prevents trades
only when the forecast magnitude exceeds a transaction-cost-based
threshold, sharply reduces turnover and restores profitability."

This iteration extracts and tests the GENERALIZABLE technique (a
deadband/minimum-signal-magnitude filter sized relative to transaction
costs, applied on top of a directional signal to suppress low-conviction
trades) rather than reproducing the paper's ML forecasting pipeline. 0
prior "cost-aware deadband" / "minimum signal magnitude" entries in this
repo's knowledge base -- every prior EMA/MACD/momentum crossover strategy
in this repo trades on every sign flip regardless of how small the
crossover margin is.

Applied here to a simple, already-well-understood base signal (fast/slow
EMA crossover on BTC/USDT and ETH/USDT) so the ONLY new variable under
test is the deadband filter itself, isolating its effect:

Signal logic
------------
- ema_fast, ema_slow: standard EMA crossover (fast > slow = bullish raw
  signal).
- raw_signal_strength = (ema_fast - ema_slow) / close (normalized
  crossover margin, analogous to the paper's "forecast magnitude").
- deadband_threshold: minimum |raw_signal_strength| required to actually
  ACT on a signal flip; below this magnitude, hold the PREVIOUS position
  instead of flipping (this is the paper's "cost-aware execution filter"
  -- prevents a trade only when the margin doesn't clear the threshold).
- Position stays 1 (long) while ema_fast > ema_slow AND either
  raw_signal_strength has cleared deadband_threshold at some point since
  the last flip, or we're continuing an existing long; flips to 0 only
  when ema_fast < ema_slow AND |raw_signal_strength| >= deadband_threshold
  (mirror condition for entering long from flat).
- No time-stop (this is testing the deadband mechanism, not adding an
  unrelated exit rule).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if isinstance(df.index, pd.DatetimeIndex):
        # Resample native (possibly hourly) bars to daily.
        daily = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        return daily
    return df


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 12,
    ema_slow: int = 26,
    deadband_threshold: float = 0.005,
) -> pd.Series:
    """Return a {0,1} long/flat position series with a cost-aware deadband
    filter suppressing low-conviction crossover flips."""
    df = _prep(price_df)
    close = df["close"]

    fast = close.ewm(span=ema_fast, adjust=False).mean()
    slow = close.ewm(span=ema_slow, adjust=False).mean()
    raw_signal_strength = (fast - slow) / close

    bullish_raw = fast > slow
    clears_deadband = raw_signal_strength.abs() >= deadband_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    current = 0
    for i in range(len(close)):
        if pd.isna(raw_signal_strength.iloc[i]):
            position.iloc[i] = current
            continue
        want_long = bool(bullish_raw.iloc[i])
        if clears_deadband.iloc[i]:
            # Only act on the signal (flip position) when the crossover
            # margin clears the cost-aware deadband threshold.
            current = 1 if want_long else 0
        # else: hold previous position (deadband suppresses the trade)
        position.iloc[i] = current

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
