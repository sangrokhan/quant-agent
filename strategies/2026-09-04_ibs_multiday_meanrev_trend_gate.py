"""Strategy: Multi-day averaged Internal Bar Strength (IBS) mean reversion,
gated by a long-term uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-158):
Internal Bar Strength (IBS) = (close - low) / (high - low), scaled 0-100,
measures where a bar's close sits within its own high-low range. Per Cesar
Alvarez's (Alvarez Quant Trading) IBS mean-reversion research, a LOW IBS
(close near the day's low) predicts the next bar tends to close higher
(mean reversion): his bucket test found IBS < 25 keeps 63% of a base
mean-reversion strategy's trades while improving average P/L by 21%. He
explicitly notes single-day IBS alone (no trend filter, no averaging) has
not worked well standalone in his own testing, and suggests -- untested by
him -- averaging IBS over N bars (multi-day IBS) as a promising extension.
This strategy implements exactly that untested extension: an N-day rolling
average of daily IBS values, entering long when the averaged IBS drops
below an oversold threshold (i.e. price has been persistently closing near
its daily lows over several days -- a stronger, less noisy signal than a
single day's IBS), gated by a 200-day SMA uptrend filter (buying dips
within an established uptrend, not catching falling knives) per Alvarez's
own base-strategy design which always includes a trend/regime filter.

Signal logic
------------
- Daily IBS_t = (close_t - low_t) / (high_t - low_t), scaled 0-100
  (guarded against zero-range bars).
- Averaged IBS over `ibs_window` days (default 3).
- Long entry: averaged IBS crosses below `entry_threshold` (default 25)
  AND close > SMA(trend_window) (uptrend regime, per Alvarez's own base
  strategy always requiring close > 200d MA).
- Exit: averaged IBS crosses back above `exit_threshold` (default 60,
  price closing well off its recent lows again), OR the trend filter
  breaks (close < SMA(trend_window)), OR a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ibs(df: pd.DataFrame) -> pd.Series:
    import numpy as np

    high = df["high"]
    low = df["low"]
    close = df["close"]
    rng = (high - low).replace(0.0, np.nan)
    ibs = (close - low) / rng * 100.0
    return ibs.astype(float).fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    ibs_window: int = 3,
    entry_threshold: float = 25.0,
    exit_threshold: float = 60.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ibs = _ibs(df)
    avg_ibs = ibs.rolling(ibs_window).mean()
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (avg_ibs < entry_threshold) & uptrend.fillna(False)
    exit_reverted = avg_ibs > exit_threshold
    exit_regime_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_reverted.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
