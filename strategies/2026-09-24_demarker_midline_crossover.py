"""Strategy: DeMarker (DeM) Midline Crossover -- long-only 0.5-threshold
momentum-shift entry, distinct from this repo's prior DeMarker techniques.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-027):
Per Tradeworks' "DeMarker (DeM) Indicator Strategy for Automated Trading"
(https://tradeworks.io/indicators/demarker, snippet + Google AI-overview
synthesis read via browser_exec after web_search DDGS backend TLS
RequestError): "The DeMarker Midline Crossover strategy uses the 0.5
threshold to identify shifts in buying and selling pressure, testing
entries when momentum changes." This is a *centerline* crossover technique
(DeM crossing its own 0.5 midpoint), distinct from this repo's 4 prior
DeMarker entries which all used either the 0.30/0.70 overbought/oversold
threshold-cross-and-bounce (2026-09-04-154, accepted QQQ), swing-low
divergence (2026-09-10-126, rejected), continuous z-score/tanh sizing dial
(2026-09-14-132, accepted QQQ+crypto), or a 5-day-window oversold-level
entry on TLT with no trend filter (2026-09-20-067/068, both rejected).

DeM formula (Tom DeMark, confirmed across all sources):
    DeMax = max(high - high[1], 0)
    DeMin = max(low[1] - low, 0)
    DeM   = SMA(DeMax, n) / (SMA(DeMax, n) + SMA(DeMin, n))   # bounded [0,1]

Signal logic
------------
- Compute DeM(dem_window) on daily OHLC.
- Long entry: DeM crosses ABOVE 0.5 (buying pressure taking over) AND
  close > SMA(trend_window) (long-term uptrend regime -- this repo's
  established fix for raw oscillator-crossover signals that fail
  standalone, per 2026-09-04-154's own trend-gate pattern).
- Exit: DeM crosses back BELOW 0.5 (momentum shift reversing), OR close
  drops below the trend SMA (regime flip), OR a max_hold_days time-stop.
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
    midline: float = 0.5,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dem = _demarker(df, dem_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    cross_above = (dem > midline) & (dem.shift(1) <= midline)
    cross_below = (dem < midline) & (dem.shift(1) >= midline)

    entry = cross_above & uptrend.fillna(False)
    exit_regime_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_below.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
