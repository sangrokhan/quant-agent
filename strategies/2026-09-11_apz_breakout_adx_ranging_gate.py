"""Strategy: Adaptive Price Zone (APZ) breakout, gated by a low-ADX ranging-market filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-012):
Lee Leibfarth's Adaptive Price Zone (APZ, TASC Sep 2006, via
https://tickeron.com/fin-articles/adaptive-price-zone-indicator-explained/
and the AI-overview-synthesized Google SERP corroborated by
NinjaTrader/TradingView pages): APZ forms dynamic upper/lower bands using a
short-term double-smoothed EMA of price plus a double-smoothed EMA of the
high-low range as the band-width term. Bands expand in high volatility and
contract in quiet/choppy periods.

This repo's prior APZ entry (2026-09-07-011, rejected) tested a
MEAN-REVERSION interpretation (long entry when close crosses BELOW the
lower band, i.e. betting on reversion back to the centerline). This
iteration tests the DISTINCT BREAKOUT interpretation instead: per the
Google AI-overview synthesis of Tickeron/NinjaTrader material, "Buy Signal:
Enter a long position when the asset price crosses above the upper band of
the APZ indicator. Many traders pair this with a trend filter like the
Average Directional Index (ADX) staying below 30 to confirm a non-trending,
ranging market" (i.e. treat the breakout as a volatility-expansion signal
specifically when ADX signals the market ISN'T already in a strong trend --
the opposite of most trend-following ADX>25 gates used elsewhere in this
repo). Exit: price reverts back to the centerline, or momentum reverses, or
a max_hold_days time-stop.

APZ construction (identical to this repo's 2026-09-07-011 for
comparability): centerline = double-smoothed EMA(hl2, ema_period);
band_width = band_pct * double-smoothed EMA(high-low range, ema_period);
upper_band = centerline + band_width; lower_band = centerline - band_width.
ADX(14) computed via the standard Wilder +DI/-DI/DX/ADX recursion.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _double_ema(series: pd.Series, period: int) -> pd.Series:
    e1 = series.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period, adjust=False).mean()
    return e2


def _wilder_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0, float("nan")))
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0, float("nan")))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 20,
    band_pct: float = 2.0,
    adx_period: int = 14,
    adx_threshold: float = 30.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    hl2 = (high + low) / 2.0
    hl_range = high - low

    centerline = _double_ema(hl2, ema_period)
    band_width = band_pct * _double_ema(hl_range, ema_period)
    upper_band = centerline + band_width

    adx = _wilder_adx(high, low, close, adx_period)
    ranging_regime = adx < adx_threshold

    cross_above_upper = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
    entry = cross_above_upper & ranging_regime.fillna(False)
    exit_centerline = close < centerline

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_centerline.iloc[i]) or held >= max_hold_days:
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
