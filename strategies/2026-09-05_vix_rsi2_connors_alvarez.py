"""Strategy: Connors/Alvarez VIX RSI (2-period RSI applied to the VIX index).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-052):
Per Larry Connors & Cesar Alvarez's book "Short Term Trading Strategies
That Work" (as disclosed by easylanguagemastery.com's "Profit By Combining
RSI And VIX" article), a 2-period RSI computed on the VIX INDEX ITSELF
(not on the price of the tradable asset) spiking above 90 signals an
acute, already-fading fear spike -- a buy signal for the underlying
equity index -- when confirmed by the price's own oversold RSI(2) reading
and a long-term uptrend filter. This is the first VIX strategy in this
repo to apply an RSI OSCILLATOR to the VIX series itself, rather than
using VIX's raw level, its SMA/Bollinger Band, or VIX/VIX3M term
structure (distinct from 2026-09-04-103, 2026-09-04-157, 2026-09-05-021,
2026-09-05-028, 2026-09-05-044).

Signal logic (exact rules per source)
--------------------------------------
1. Tradable-asset close is above its own 200-day SMA (long-term uptrend
   filter).
2. RSI(2) of the tradable asset's close is below `price_rsi_entry` (30).
3. RSI(2) computed on the VIX's own close series is above `vix_rsi_entry`
   (90) -- the actual entry trigger.
Buy when all three align on the same day.

Exit: RSI(2) of the tradable asset's close rises above `price_rsi_exit`
(65), or a `max_hold_days` time-stop (source's own rules have no stop, a
backstop is added here matching this repo's convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)

Note: `price_df` is the TRADABLE asset (QQQ/SPY/BTC-USDT/ETH-USDT); VIX
data is fetched internally via data/loaders.load_equity("^VIX", ...)
aligned to price_df's date range, since VIX itself isn't the position --
it's the signal source (per this repo's established VIX-strategy pattern,
see strategies/2026-09-05_cvr3_vix_market_timing.py).
"""

from __future__ import annotations

import sys
import os
from datetime import timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.DataFrame:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    vix = load_equity("^VIX", start, end)
    return _prep(vix)


def _rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    price_rsi_entry: float = 30.0,
    vix_rsi_entry: float = 90.0,
    price_rsi_exit: float = 65.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series on the TRADABLE asset."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    price_rsi2 = _rsi(close, period=2)

    vix = _fetch_vix(df.index)
    vix_rsi2 = _rsi(vix["close"], period=2).reindex(df.index).ffill()

    uptrend = close > sma_trend
    entry_signal = (
        uptrend
        & (price_rsi2 < price_rsi_entry)
        & (vix_rsi2 > vix_rsi_entry)
    ).fillna(False)
    exit_signal = (price_rsi2 > price_rsi_exit).fillna(False)

    valid = sma_trend.notna() & price_rsi2.notna() & vix_rsi2.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
