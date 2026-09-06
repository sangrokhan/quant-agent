"""Strategy: Adaptive Price Zone (APZ, Leibfarth 2006) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-011):
Per TradingView's APZ script description (Lee Leibfarth, 2006, via
https://www.tradingview.com/script/AzkoAdVR/): "It works by taking the
double-smoothed average of the volatility from 5 days and adding/
subtracting it from the average price of the day (hl2)." APZ differs
mechanically from the already-tested Bollinger Bands (std-dev of close) and
Keltner Channels (single-smoothed ATR envelope) in this repo: both the
centerline AND the band width are DOUBLE exponentially smoothed (EMA of EMA)
-- of hl2 for the centerline and of the high-low range for the band width --
which should produce a slower, less noise-reactive band than either prior
band-based strategy. Hypothesis: price closing below the lower APZ band
signals an overextended short-term move that mean-reverts back toward the
double-smoothed centerline; exit on close crossing back above the centerline
(or a max-hold time-stop to avoid indefinite holds in a trending regime).

Signal logic
------------
- smooth1 = EMA(hl2, window); centerline = EMA(smooth1, window)  (double EMA
  of the typical price -- the "adaptive" price center)
- vol1 = EMA(high-low, window); vol_smooth = EMA(vol1, window)  (double EMA
  of daily range -- the "adaptive" volatility measure)
- upper_band = centerline + band_pct * vol_smooth
- lower_band = centerline - band_pct * vol_smooth
- Entry (long): close crosses below lower_band.
- Exit: close crosses back above centerline, OR max_hold_days elapsed
  (avoid indefinite holds if the move keeps trending down instead of
  reverting).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 5,
    band_pct: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    hl2 = (df["high"] + df["low"]) / 2.0
    rng = df["high"] - df["low"]

    smooth1 = hl2.ewm(span=window, adjust=False).mean()
    centerline = smooth1.ewm(span=window, adjust=False).mean()

    vol1 = rng.ewm(span=window, adjust=False).mean()
    vol_smooth = vol1.ewm(span=window, adjust=False).mean()

    lower_band = centerline - band_pct * vol_smooth
    upper_band_mid = centerline  # exit target: revert to centerline

    entry = close < lower_band
    exit_meanrev = close > upper_band_mid

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
