"""Strategy: Positive Volume Index (PVI) crossing its own moving average,
gated by a long-term trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-001):
PVI (Norman Fosback / classic accumulation-volume index, mirror of the
already-tested Negative Volume Index) accumulates the day's percentage price
change only on days where volume INCREASED from the prior day -- the
canonical interpretation (per HPotter's widely-used TradingView PVI/NVI
backtest script) is that PVI tracks "the crowd"/high-volume-driven price
moves, versus NVI's "smart money"/low-volume moves. The standard systematic
entry (same TradingView script, and PineScriptForge's NQ PVI backtest page)
is: go long when PVI crosses above its own N-period moving average
(canonical 255-period, ~1yr), confirmed by price above a long-term trend
filter; exit on the reverse crossover. This is the volume-increase mirror of
2026-09-04-139 (NVI+trend-filter, accepted SPY only) -- distinct signal
construction (opposite volume-day condition) tested here as its own
hypothesis, not assumed to behave identically to NVI.

Signal logic
------------
- PVI_t = PVI_{t-1} * (1 + close_pct_change_t) if volume_t > volume_{t-1},
  else PVI_t = PVI_{t-1} (unchanged on flat/falling-volume days). Seed
  PVI_0 = 1000 (standard convention, mirrors NVI seed).
- pvi_ma = simple moving average of PVI over pvi_ma_window (canonical
  literature value: 255; also test shorter for responsiveness).
- trend_filter: close > close.rolling(trend_window).mean() (long-term
  uptrend confirmation, canonical value 200).
- Entry (long): PVI crosses above pvi_ma AND trend_filter is true.
- Exit: PVI crosses below pvi_ma, OR trend_filter flips false, OR a
  max_hold_days time-stop backstop (PVI/MA crossovers can be infrequent
  given the long lookback -- avoid indefinite holds).
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


def _positive_volume_index(close: pd.Series, volume: pd.Series) -> pd.Series:
    pct_change = close.pct_change().fillna(0.0)
    vol_increased = volume > volume.shift(1)
    pvi = pd.Series(index=close.index, dtype=float)
    pvi.iloc[0] = 1000.0
    for i in range(1, len(close)):
        if bool(vol_increased.iloc[i]):
            pvi.iloc[i] = pvi.iloc[i - 1] * (1.0 + pct_change.iloc[i])
        else:
            pvi.iloc[i] = pvi.iloc[i - 1]
    return pvi


def generate_signals(
    price_df: pd.DataFrame,
    pvi_ma_window: int = 255,
    trend_window: int = 200,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    pvi = _positive_volume_index(close, volume)
    pvi_ma = pvi.rolling(pvi_ma_window, min_periods=max(5, pvi_ma_window // 5)).mean()
    trend_ma = close.rolling(trend_window, min_periods=max(5, trend_window // 5)).mean()

    trend_ok = close > trend_ma
    pvi_above = pvi > pvi_ma

    entry = pvi_above & trend_ok.fillna(False)
    exit_cross = (~pvi_above) | (~trend_ok.fillna(False))

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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
