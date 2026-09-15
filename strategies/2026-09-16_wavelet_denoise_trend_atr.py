"""Strategy: Rolling-window causal wavelet-denoised trend + ATR-band
breakout confirmation.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary of wavelet-denoising trend-trading
writeups (Medium/Sofien Kaabar CFA, MDPI, ResearchGate, TradingView cited;
read via `browser_exec` fallback after `web_search`'s DDGS backend failed
with the same Yahoo/TLS RequestError as this trigger's prior iterations):
decompose the close-price series with a Discrete Wavelet Transform (DWT,
Daubechies db4 here), zero out (threshold away) the highest-frequency
detail coefficients to remove short-term noise, and reconstruct an
approximate "denoised trend" path. The source's own causal-processing rule
(explicitly called out to avoid look-ahead/future-data leakage) is: compute
the transform using ONLY past and current bars each time, i.e. re-run the
wavelet decomposition on a ROLLING trailing window at every bar rather than
once on the full historical series (a single full-series DWT would leak
future information backward through the boundary coefficients into "past"
reconstructed values). Entry: go long when the denoised trend line's slope
turns positive AND price closes outside an ATR band around the
reconstructed trend (source's "confirmation filter": require a close
outside the ATR band to confirm the state change is structural, not a
false break, mirroring the source's Average-True-Range-band gate). Exit:
symmetric -- flat when denoised slope turns non-positive or price closes
back inside the ATR band.

First wavelet-transform-based strategy in this repo (1 prior entry tag
match, but that was Hilbert-Transform-only, a fundamentally different
signal-processing construction -- true Discrete Wavelet Transform has zero
prior matches). Distinct from every EMA/SMA/Kalman/Ehlers-filter smoothing
strategy already tested (Kalman, Ehlers instantaneous trendline,
adaptive-SS, roofing filter, super-passband) since DWT multi-resolution
denoising is a fundamentally different (non-recursive, block-based
multi-scale) smoothing construction than any single-pole/EMA-chain filter
already in this repo.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pywt


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _denoise_last_value(window: np.ndarray, wavelet: str, level: int) -> float:
    """Run a DWT decomposition on `window` (oldest->newest), zero out the
    finest-detail coefficients, reconstruct, and return only the LAST
    reconstructed value (the value at the current bar, using only data up
    to and including this bar -- no look-ahead)."""
    n = len(window)
    max_level = pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)
    lvl = min(level, max_level)
    if lvl < 1:
        return float(window[-1])
    coeffs = pywt.wavedec(window, wavelet, level=lvl)
    # Zero the finest 1-2 detail levels (highest-frequency noise), keep
    # the approximation and coarser detail levels.
    coeffs = list(coeffs)
    for i in range(1, min(2, len(coeffs) - 1) + 1):
        coeffs[-i] = np.zeros_like(coeffs[-i])
    recon = pywt.waverec(coeffs, wavelet)
    # waverec can return a slightly different length than n; take the last
    # `n` elements' final value, aligned to the input window's last index.
    return float(recon[:n][-1])


def _rolling_wavelet_trend(
    close: pd.Series, window: int, wavelet: str = "db4", level: int = 3
) -> pd.Series:
    """Causal rolling-window wavelet-denoised trend: at each bar t, denoise
    using ONLY close[t-window+1 : t+1] and take the reconstructed value at
    t. This is O(n) separate small DWTs -- deliberately not a single
    full-series DWT (which would leak future info via boundary effects)."""
    values = close.to_numpy()
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        w = values[i - window + 1 : i + 1].copy()
        out[i] = _denoise_last_value(w, wavelet, level)
    return pd.Series(out, index=close.index)


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prior_close).abs(), (low - prior_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    wavelet_window: int = 60,
    wavelet: str = "db4",
    wavelet_level: int = 3,
    atr_window: int = 14,
    atr_mult: float = 1.0,
    slope_lookback: int = 3,
) -> pd.Series:
    """0/1 long-only position series.

    Entry/hold long when: (a) the rolling wavelet-denoised trend's slope
    (change over `slope_lookback` bars) is positive, AND (b) close is
    above (denoised_trend + atr_mult * ATR) -- the ATR-band confirmation
    that the state change is structural, not a false break. Flat
    otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    trend = _rolling_wavelet_trend(close, wavelet_window, wavelet=wavelet, level=wavelet_level)
    trend_slope = trend.diff(slope_lookback)

    atr = _atr(df, window=atr_window)
    upper_band = trend + atr_mult * atr

    long_cond = (trend_slope > 0) & (close > upper_band)
    position = long_cond.fillna(False).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    wavelet_window: int = 60,
    wavelet: str = "db4",
    wavelet_level: int = 3,
    atr_window: int = 14,
    atr_mult: float = 1.0,
    slope_lookback: int = 3,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        wavelet_window=wavelet_window,
        wavelet=wavelet,
        wavelet_level=wavelet_level,
        atr_window=atr_window,
        atr_mult=atr_mult,
        slope_lookback=slope_lookback,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
