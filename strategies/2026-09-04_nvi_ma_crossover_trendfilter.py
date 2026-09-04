"""Strategy: Negative Volume Index (NVI) crossing its own moving average,
gated by a long-term trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-139):
NVI (Paul Dysart, popularized by Norman Fosback) accumulates the day's
percentage price change only on days where volume DECREASED from the prior
day -- the idea being that low-volume days reflect "smart money"/informed
positioning versus high-volume days dominated by "the crowd". Per Google's
AI-overview synthesis of cTrader/LightningChart/Earn2Trade explainers, the
canonical systematic entry is: go long when the NVI line crosses above its
own N-period moving average (smart money accumulating), confirmed by price
being above its own long-term (200d) moving average trend filter; exit when
NVI crosses back below its moving average, or a max-hold time-stop backstop.
This is the first Negative-Volume-Index (accumulation/distribution family,
distinct from OBV/PVT/AD-line already tested) strategy tried in this repo.

Signal logic
------------
- NVI_t = NVI_{t-1} * (1 + close_pct_change_t) if volume_t < volume_{t-1},
  else NVI_t = NVI_{t-1} (unchanged on flat/rising-volume days). Seed
  NVI_0 = 1000 (standard convention).
- nvi_ma = simple moving average of NVI over nvi_ma_window (canonical
  literature value: 255, ~1 trading year; also test shorter for
  responsiveness).
- trend_filter: close > close.rolling(trend_window).mean() (long-term
  uptrend confirmation, canonical value 200).
- Entry (long): NVI crosses above nvi_ma AND trend_filter is true.
- Exit: NVI crosses below nvi_ma, OR trend_filter flips false, OR a
  max_hold_days time-stop backstop (NVI/MA crossovers can be very
  infrequent given the long lookback -- avoid indefinite holds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _negative_volume_index(close: pd.Series, volume: pd.Series) -> pd.Series:
    pct_change = close.pct_change().fillna(0.0)
    vol_decreased = volume < volume.shift(1)
    nvi = pd.Series(index=close.index, dtype=float)
    nvi.iloc[0] = 1000.0
    for i in range(1, len(close)):
        if bool(vol_decreased.iloc[i]):
            nvi.iloc[i] = nvi.iloc[i - 1] * (1.0 + pct_change.iloc[i])
        else:
            nvi.iloc[i] = nvi.iloc[i - 1]
    return nvi


def generate_signals(
    price_df: pd.DataFrame,
    nvi_ma_window: int = 255,
    trend_window: int = 200,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    nvi = _negative_volume_index(close, volume)
    nvi_ma = nvi.rolling(nvi_ma_window, min_periods=max(5, nvi_ma_window // 5)).mean()
    trend_ma = close.rolling(trend_window, min_periods=max(5, trend_window // 5)).mean()

    trend_ok = close > trend_ma
    nvi_above = nvi > nvi_ma

    entry = nvi_above & trend_ok.fillna(False)
    exit_cross = (~nvi_above) | (~trend_ok.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
