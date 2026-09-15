"""Strategy: Nadaraya-Watson Envelope (LuxAlgo) mean-reversion, non-repainting
endpoint estimator.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
LuxAlgo's Nadaraya-Watson Envelope (2021) estimates the underlying price
trend via Gaussian-kernel-weighted regression and builds an envelope around
the fit using the mean absolute deviation of price from that fit. Per the
exact disclosed Pine v5 source
(https://www.tradingview.com/script/Iko0E2kL-Nadaraya-Watson-Envelope-LuxAlgo/,
non-repainting "endpoint" mode -- backward-looking only, safe for
backtesting, unlike the default repainting mode which recomputes the
full-window fit on every new bar):

    gauss(x, h) = exp(-x^2 / (2*h^2))
    coefs[i] = gauss(i, h)  for i = 0..W-1        (computed once, fixed)
    out_t = sum_i(price[t-i] * coefs[i]) / sum(coefs)
    mae_t = SMA(|price - out|, W) * mult
    upper_t = out_t + mae_t
    lower_t = out_t - mae_t

Per LuxAlgo's own disclosed trading rule: price crossing below the lower
envelope flags a stretched decline relative to the kernel-regression trend
estimate, a mean-reversion long setup; crossing above the upper envelope is
the mirror short-side (not used here, long-only per this repo). LuxAlgo's
own caveat: "nothing suggests this envelope outperforms traditional band
tools" -- tested honestly here rather than assumed to work. First
Nadaraya-Watson-family strategy in this repo -- distinct from every other
band/envelope construction already tested (Bollinger, Keltner, STARC,
Acceleration Bands, Elder AutoEnvelope, Fractal Chaos Bands) via its unique
Gaussian-kernel-weighted-regression center line (not a simple/exponential
moving average).

Signal logic
------------
- Long (position=1) entry: close crosses below the lower envelope band
  (stretched decline).
- Exit: close crosses back above the kernel-regression center line `out`
  (reversion to trend), or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _nw_envelope(close: pd.Series, bandwidth: float, mult: float, window: int) -> tuple:
    """Non-repainting endpoint Nadaraya-Watson kernel regression + envelope.

    Uses a fixed-length trailing window (default 100 bars, ample for the
    Gaussian kernel to decay to ~0 weight at typical bandwidth<=20 values)
    instead of the source's full 500-bar window, for efficiency -- the
    Gaussian weights are negligible beyond a few multiples of `bandwidth`.
    """
    idx = np.arange(window, dtype=float)
    coefs = np.exp(-(idx ** 2) / (2.0 * bandwidth * bandwidth))
    denom = coefs.sum()

    values = close.to_numpy()
    n = len(values)
    out = np.full(n, np.nan)

    for t in range(n):
        w = min(window, t + 1)
        # price[t-i] for i=0..w-1, weighted by coefs[0..w-1]
        window_vals = values[t - w + 1 : t + 1][::-1]
        out[t] = np.dot(window_vals, coefs[:w]) / coefs[:w].sum()

    out_series = pd.Series(out, index=close.index)
    abs_dev = (close - out_series).abs()
    mae = abs_dev.rolling(window, min_periods=1).mean() * mult

    upper = out_series + mae
    lower = out_series - mae
    return out_series, upper, lower


def generate_signals(
    price_df: pd.DataFrame,
    bandwidth: float = 8.0,
    mult: float = 3.0,
    window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the NW-envelope
    mean-reversion rule (long on lower-band crossunder, exit on
    center-line reversion or time-stop).
    """
    df = _prep(price_df)
    close = df["close"]
    out, upper, lower = _nw_envelope(close, bandwidth, mult, window)

    entry = (close < lower) & (close.shift(1) >= lower.shift(1))
    exit_ = close > out

    n = len(df)
    pos = np.zeros(n, dtype=int)
    in_pos = False
    hold = 0
    entry_arr = entry.fillna(False).to_numpy()
    exit_arr = exit_.fillna(False).to_numpy()
    for i in range(n):
        if in_pos:
            hold += 1
            if exit_arr[i] or hold > max_hold_days:
                in_pos = False
                hold = 0
            else:
                pos[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold = 1
                pos[i] = 1
    return pd.Series(pos, index=df.index)


def generate_returns(
    price_df: pd.DataFrame,
    bandwidth: float = 8.0,
    mult: float = 3.0,
    window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, bandwidth=bandwidth, mult=mult, window=window, max_hold_days=max_hold_days
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    return position.shift(1).fillna(0) * daily_ret
