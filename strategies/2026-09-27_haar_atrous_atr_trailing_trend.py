"""Strategy: Undecimated (a-trous) Haar wavelet denoised trend + ATR trailing band.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per QuantAlgo's "Wavelet Transform Trend" TradingView indicator
(https://www.tradingview.com/script/YI4KzWFT-Wavelet-Transform-Trend-QuantAlgo/,
read via browser_exec — web_extract cannot fetch TradingView, ddgs backend is
search-only), a multi-level UNDECIMATED (a-trous) Haar wavelet cascade
denoises the price path without downsampling (fully shift-invariant, unlike
the previously-tested standard discrete wavelet transform in this repo,
2026-09-16-080, which used a decimated db4 DWT and was rejected for
equity/crypto). The denoised path is then wrapped in an ATR-based trailing
band (SuperTrend-style: band only trails favorably and freezes otherwise),
and the trend state flips only on a confirmed close beyond the trailing
band — this ratchet mechanic is the key difference from 2026-09-16-080's
simple ATR-band breakout-confirmation (non-ratcheting) approach.

Cascade (dilated, no downsampling — each stage doubles the filter's
effective span so every bar keeps a coefficient at every scale):
    a0 = close
    for level i in 1..wavelet_levels:
        shift_i = 2 ** (i - 1)
        a_i = (a_{i-1} + a_{i-1}.shift(shift_i)) / 2
    denoised_trend = a_{wavelet_levels}   (deepest approximation only,
                                            i.e. Wavelet Approximation Only
                                            mode per the source, simplest
                                            and most literal translation)

Long-only, following this repo's standard trend-following convention:
    - long (1) while price is in a confirmed bullish state (close closed
      above the ratcheting lower trailing band at some point and hasn't
      since closed back below the ratcheting upper band)
    - flat (0) otherwise

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here -- handled separately by check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atrous_haar_trend(close: pd.Series, wavelet_levels: int) -> pd.Series:
    """Undecimated (a-trous) Haar wavelet cascade -> deepest approximation."""
    a = close.astype(float)
    for i in range(1, wavelet_levels + 1):
        shift = 2 ** (i - 1)
        a = (a + a.shift(shift)) / 2.0
    return a


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def _trend_state(
    close: pd.Series, trend_path: pd.Series, atr: pd.Series, atr_mult: float
) -> pd.Series:
    """Compute the ratcheting ATR-band trend state (1=bullish, 0=bearish)."""
    raw_upper = trend_path + atr_mult * atr
    raw_lower = trend_path - atr_mult * atr

    n = len(close)
    upper_band = np.full(n, np.nan)
    lower_band = np.full(n, np.nan)
    state = np.zeros(n, dtype=int)  # 0 = bearish/flat, 1 = bullish

    close_v = close.values
    raw_upper_v = raw_upper.values
    raw_lower_v = raw_lower.values

    first_valid = None
    for i in range(n):
        if np.isnan(raw_upper_v[i]) or np.isnan(raw_lower_v[i]) or np.isnan(close_v[i]):
            continue
        if first_valid is None:
            first_valid = i
            upper_band[i] = raw_upper_v[i]
            lower_band[i] = raw_lower_v[i]
            state[i] = 0
            continue

        prev_upper = upper_band[i - 1]
        prev_lower = lower_band[i - 1]
        prev_close = close_v[i - 1]

        # Ratchet: lower band only trails upward while price stays above it;
        # upper band only trails downward while price stays below it.
        if raw_lower_v[i] > prev_lower or prev_close < prev_lower:
            lower_band[i] = raw_lower_v[i]
        else:
            lower_band[i] = prev_lower

        if raw_upper_v[i] < prev_upper or prev_close > prev_upper:
            upper_band[i] = raw_upper_v[i]
        else:
            upper_band[i] = prev_upper

        prev_state = state[i - 1]
        if close_v[i] > upper_band[i]:
            state[i] = 1
        elif close_v[i] < lower_band[i]:
            state[i] = 0
        else:
            state[i] = prev_state

    return pd.Series(state, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    wavelet_period: int = 40,
    wavelet_levels: int = 3,
    atr_window: int = 14,
    atr_mult: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    wavelet_period is accepted for interface/documentation symmetry with the
    source indicator's "Wavelet Period" concept but the a-trous cascade's
    effective span is fully determined by wavelet_levels (2**levels bars);
    wavelet_period is used only to clamp wavelet_levels so the deepest
    approximation's span doesn't exceed wavelet_period.
    """
    df = _prep(price_df)
    close = df["close"]

    # Clamp levels so effective cascade span (2**levels) doesn't exceed period.
    max_levels_from_period = max(1, int(np.log2(max(2, wavelet_period))))
    levels = max(1, min(wavelet_levels, max_levels_from_period))

    trend_path = _atrous_haar_trend(close, levels)
    atr = _atr(df, atr_window)
    state = _trend_state(close, trend_path, atr, atr_mult)

    signal = state.shift(1).fillna(0).astype(int)  # trade on next bar's open (avoid lookahead)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    wavelet_period: int = 40,
    wavelet_levels: int = 3,
    atr_window: int = 14,
    atr_mult: float = 2.0,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        wavelet_period=wavelet_period,
        wavelet_levels=wavelet_levels,
        atr_window=atr_window,
        atr_mult=atr_mult,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions.shift(0) * daily_ret  # positions already shifted in generate_signals
    return strat_ret.fillna(0.0)
