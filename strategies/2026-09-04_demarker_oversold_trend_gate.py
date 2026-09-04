"""Strategy: DeMarker (DeM) oversold-exhaustion reversal, gated by a long-term
uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-154):
The DeMarker oscillator (Thomas DeMark) compares the current bar's high/low
extremes to the prior bar's to measure buying/selling exhaustion:
    DeMax = max(high - high[1], 0)
    DeMin = max(low[1] - low, 0)
    DeM   = SMA(DeMax, n) / (SMA(DeMax, n) + SMA(DeMin, n))   # 0..1 scale
Per LiteFinance's DeMarker explainer, DeM < 0.30 signals downside exhaustion
(oversold) and DeM > 0.70 signals upside exhaustion (overbought), default
n=14. Standalone oscillator-exhaustion strategies in this repo (RWI, VHF)
were rejected for lacking a trend filter and holding up only in low-vol
regimes; here we explicitly require the long-term trend to already be up
(close > 200d SMA) before trusting an oversold bounce, distinct from
Connors RSI(2) (2026-09-04-113, uses composite RSI/streak/ROC oscillator)
and TD Sequential (2026-09-04-032, bar-counting setup, not high/low ratio
exhaustion) already tried.

Signal logic
------------
- Compute DeM(dem_window) on daily OHLC.
- Long entry: DeM crosses back ABOVE oversold_threshold from below (bounce
  confirmed, not just touching oversold) AND close > SMA(trend_window)
  (long-term uptrend regime).
- Exit: DeM crosses above overbought_threshold (exhaustion of the bounce),
  OR close drops back below the trend SMA (regime flip), OR a max_hold_days
  time-stop.
- Flat otherwise.

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


def _demarker(df: pd.DataFrame, dem_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    de_max = (high - high.shift(1)).clip(lower=0.0)
    de_min = (low.shift(1) - low).clip(lower=0.0)
    sma_max = de_max.rolling(dem_window).mean()
    sma_min = de_min.rolling(dem_window).mean()
    denom = sma_max + sma_min
    dem = (sma_max / denom).where(denom > 0, 0.5)
    return dem


def generate_signals(
    price_df: pd.DataFrame,
    dem_window: int = 14,
    oversold_threshold: float = 0.30,
    overbought_threshold: float = 0.70,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dem = _demarker(df, dem_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    oversold_bounce = (dem > oversold_threshold) & (dem.shift(1) <= oversold_threshold)
    entry = oversold_bounce & uptrend.fillna(False)
    exit_overbought = dem > overbought_threshold
    exit_regime_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
