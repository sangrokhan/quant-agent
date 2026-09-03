"""Strategy: OBV-momentum trend confirmation (OBV crosses its own EMA,
gated by a price trend filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-027):
Per TradingCompendium's OBV guide
(https://tradingcompendium.com/en/technical-indicators/obv-on-balance-volume):
On-Balance Volume (cumulative running sum, +volume on up-close days,
-volume on down-close days) is best used as a CONFIRMATION filter, not a
standalone signal -- the source explicitly warns "using it as a standalone
signal" is a common mistake, and recommends only trusting a price trend
when OBV moves the same direction. The source's only concrete numeric
variant is applying a moving average (e.g. EMA(20)) to the OBV line
itself, with crossovers of OBV vs its own EMA giving smoother/more
actionable signals. This strategy operationalizes that combination: long
when price is in an uptrend (close > SMA(200), a coarse trend filter) AND
OBV crosses above its own EMA(obv_ema_window) (volume-momentum
confirmation), exit when either condition breaks (price falls below
SMA(200), OR OBV crosses back below its EMA). First volume-based (not
price-derived) oscillator/indicator strategy tested in this repo --
distinct from every prior price-derived indicator (RSI, CCI, Bollinger,
Keltner, MACD, ADX, SuperTrend, HMA, chandelier-ATR).

Signal logic
------------
- OBV: cumulative running sum, +volume when close > prior close, -volume
  when close < prior close, unchanged when close == prior close.
- OBV_EMA = EMA(OBV, obv_ema_window).
- Trend filter: close > SMA(trend_window).
- Entry (long): close > SMA(trend_window) AND OBV crosses from <= OBV_EMA
  to > OBV_EMA (fresh volume-momentum confirmation while already in an
  uptrend).
- Exit: close <= SMA(trend_window) (trend filter breaks) OR OBV crosses
  from > OBV_EMA to <= OBV_EMA (volume momentum fades).
- Flat otherwise; long-only, no shorting.

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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff()
    signed_vol = volume.where(direction > 0, -volume)
    signed_vol = signed_vol.where(direction != 0, 0.0)
    signed_vol.iloc[0] = 0.0
    return signed_vol.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    obv_ema_window: int = 20,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    obv = _obv(close, volume)
    obv_ema = obv.ewm(span=obv_ema_window, adjust=False).mean()
    sma_trend = close.rolling(trend_window).mean()

    obv_above = obv > obv_ema
    obv_cross_up = obv_above & (~obv_above.shift(1).fillna(False))
    obv_cross_down = (~obv_above) & (obv_above.shift(1).fillna(False))

    in_uptrend = close > sma_trend
    entry = in_uptrend & obv_cross_up.fillna(False)
    exit_signal = (~in_uptrend) | obv_cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
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
