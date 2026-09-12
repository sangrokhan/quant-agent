"""Strategy: Vitali Apirine Relative VIX Strength EMA (RSEMA) crossover.

Hypothesis (see knowledge_base entry): per Vitali Apirine's TASC 3/2022
article, reproduced at
https://financial-hacker.com/the-relative-strength-exponential-moving-average/
(fully disclosed C code): a volatility-adaptive EMA of the price series,
whose smoothing rate speeds up when the VIX itself shows a strong
up-day/down-day asymmetry (analogous to an RSI-style relative-strength
split, but applied to VIX rather than the traded asset), should track
price with less lag during volatility regime shifts than a plain EMA. The
source's own naive EMA-crossover backtest on SPY was unprofitable
(vs buy-and-hold) at default untuned parameters -- this repo runs an
independent parameter grid search rather than accepting that single
untuned result as the final word.

Algorithm (fully disclosed by source):
    vix_up[t]   = vix_close[t] if vix_return[t] > 0 else 0
    vix_dn[t]   = vix_close[t] if vix_return[t] < 0 else 0
    ema_up = EMA(vix_up, ema_periods)
    ema_dn = EMA(vix_dn, ema_periods)
    rs = abs(ema_up - ema_dn) / (ema_up + ema_dn + 1e-5) * multiplier
    rate = 2 / (periods + 1) * (rs + 1)
    RSEMA[t] = rate*price[t] + (1-rate)*RSEMA[t-1]   (EMA with per-bar
        adaptive alpha = min(rate, 1))

Long-only adaptation: long when close (or a comparison EMA) crosses above
RSEMA, flat when it crosses below -- using a companion plain EMA(periods)
as the crossover partner (mirroring the source's own "RSEMA-EMA
crossover" system design) rather than raw price, to reduce whipsaw noise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series

Note: this strategy requires VIX data as an auxiliary series; the
grid/validator harness in this repo calls generate_returns(price_df,
**params) with only the PRIMARY asset's price_df, so VIX is fetched
internally via data/loaders.py's load_equity("^VIX", ...) using the
primary price_df's own date range. This means the strategy is
equity-index-relevant (VIX is a US-equity-index vol gauge) and not
economically meaningful for crypto -- expected to fail decisively there.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in price_df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


_vix_cache: dict = {}


def _load_vix(start, end) -> pd.Series:
    key = (pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())
    if key in _vix_cache:
        return _vix_cache[key]
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    vix_df = load_equity("^VIX", start=start, end=end)
    vix_df = _prep(vix_df)
    series = vix_df["close"]
    _vix_cache[key] = series
    return series


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsema(
    close: pd.Series,
    periods: int,
    ema_periods: int,
    multiplier: float,
) -> pd.Series:
    start = close.index.min()
    end = close.index.max()
    try:
        vix_close = _load_vix(start, end)
    except Exception:
        # VIX data unavailable (e.g. crypto date ranges outside VIX history,
        # or fetch failure) -- fall back to a plain EMA (rate=constant),
        # which should decisively underperform / not trigger the intended
        # adaptive edge, consistent with this strategy's equity-only scope.
        return _ema(close, periods)

    vix_close = vix_close.reindex(close.index, method="ffill").bfill()
    vix_ret = vix_close.pct_change().fillna(0.0)
    vix_up = vix_close.where(vix_ret > 0, 0.0)
    vix_dn = vix_close.where(vix_ret < 0, 0.0)

    ema_up = _ema(vix_up, ema_periods)
    ema_dn = _ema(vix_dn, ema_periods)

    rs = (ema_up - ema_dn).abs() / (ema_up + ema_dn + 1e-5) * multiplier
    rate = (2.0 / (periods + 1)) * (rs + 1.0)
    rate = rate.clip(upper=1.0)

    vals = close.to_numpy(dtype=float)
    rate_vals = rate.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    out[0] = vals[0]
    for i in range(1, len(vals)):
        a = rate_vals[i]
        out[i] = a * vals[i] + (1 - a) * out[i - 1]
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    periods: int = 10,
    ema_periods: int = 10,
    multiplier: float = 10.0,
) -> pd.Series:
    """Long when a companion EMA(periods) crosses above RSEMA, flat otherwise."""
    df = _prep(price_df)
    close = df["close"]

    rsema = _rsema(close, periods, ema_periods, multiplier)
    companion_ema = _ema(close, periods)

    position = (companion_ema > rsema).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
