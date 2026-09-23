"""Strategy: Approximate Entropy "Predictability Emergence" collapse trigger.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-035):
Per algobot.live's "Predictability Emergence Trend" strategy
(https://www.algobot.live/predictability-emergence-trend-ea-mt5/, found via
`web_search` and read via `browser_exec` for full text since `web_extract`'s
configured backend is search-only): rather than treating Approximate
Entropy (Pincus 1991) as a static regime GATE (already tested in this repo,
2026-09-08-047: "trade the SMA breakout only while ApEn is low"), this
strategy fires on a FRESH ENTROPY COLLAPSE EVENT -- the specific transition
moment when ApEn(z-scored closes) crosses DOWN through a threshold (was
>=threshold on the prior bar, now <threshold), signalling the market has
just organized itself from noise into a structured, tradable move. Once
that collapse event fires, direction comes from a least-squares regression
slope of recent closes (not from the collapse event itself, which is
direction-agnostic), confirmed by price vs. a baseline EMA (source's own
two-part directional confirmation: slope AND price-vs-EMA must agree).
Long-only adaptation of the source's long/short design per SAFETY.md.

This is a distinct construction from the two prior entropy-family entries
in this repo: 2026-09-08-047 (ApEn as a continuous *regime gate*, entry
condition = SMA-breakout AND currently-low-entropy, no "freshness"/edge
concept) and the permutation-entropy/sample-entropy variants
(2026-09-12/2026-09-21, different entropy estimators entirely). Here entry
requires the entropy value to just now be crossing the threshold on THIS
bar -- a one-shot event trigger, not a persistent state condition -- which
is the source's stated point ("fires once at the transition and does not
re-fire while entropy stays low").

Signal logic
------------
- z-score the closes inside a rolling `entropy_window`-bar window, compute
  Approximate Entropy (m=2, r=`embed_tolerance` in z-scored-std units) on
  that window (reuses this repo's existing vectorized ApEn implementation
  from strategies/2026-09-08_apen_entropy_trend_gate.py).
- Entropy collapse trigger: ApEn[t-1] >= entropy_threshold AND
  ApEn[t] < entropy_threshold (fresh down-cross only).
- Direction: least-squares regression slope of the last `slope_window`
  closes; require slope > 0 (long-only per SAFETY.md) AND close >
  EMA(baseline_ema_span) for entry confirmation.
- Exit: close crosses back below EMA(baseline_ema_span) (baseline
  confirmation breaks), OR max_hold_days time-stop (this repo's standard
  substitute for the source's ATR-based stop/trail/breakeven machinery,
  which requires intrabar tick-level position management not supported by
  this repo's daily-bar generate_returns_fn contract).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _apen_vectorized(seg: np.ndarray, m: int, r: float) -> float:
    """Vectorized approximate entropy of a short 1-D segment (reused
    construction from strategies/2026-09-08_apen_entropy_trend_gate.py)."""
    n_total = len(seg)
    if n_total < m + 2 or r <= 0 or not np.isfinite(r):
        return np.nan

    def _phi(mm: int) -> float:
        n = n_total - mm + 1
        if n <= 0:
            return np.nan
        x = np.lib.stride_tricks.sliding_window_view(seg, mm)  # (n, mm)
        diff = np.abs(x[:, None, :] - x[None, :, :]).max(axis=2)
        counts = (diff <= r).sum(axis=1) / n
        counts = np.where(counts <= 0, np.nan, counts)
        return np.nanmean(np.log(counts))

    phi_m = _phi(m)
    phi_m1 = _phi(m + 1)
    if not np.isfinite(phi_m) or not np.isfinite(phi_m1):
        return np.nan
    return phi_m - phi_m1


def _rolling_apen_of_zscored_close(close: pd.Series, entropy_window: int, m: int, embed_tolerance: float) -> pd.Series:
    """ApEn computed on the Z-SCORED closes within each rolling window (per
    source: scale-free, ignores price level/volatility, responds only to
    the shape of recent price action)."""
    vals = close.values.astype(float)
    n = len(vals)
    out = np.full(n, np.nan)
    for end in range(entropy_window, n + 1):
        seg = vals[end - entropy_window : end]
        seg = seg[~np.isnan(seg)]
        if len(seg) < entropy_window * 0.8:
            continue
        mu = np.mean(seg)
        sd = np.std(seg, ddof=0)
        if sd <= 0 or not np.isfinite(sd):
            continue
        z = (seg - mu) / sd
        out[end - 1] = _apen_vectorized(z, m, embed_tolerance)
    return pd.Series(out, index=close.index)


def _rolling_slope(close: pd.Series, slope_window: int) -> pd.Series:
    """Least-squares regression slope of the last slope_window closes."""
    x = np.arange(slope_window, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _slope(window_vals: np.ndarray) -> float:
        y = window_vals
        y_mean = y.mean()
        return float(((x - x_mean) * (y - y_mean)).sum() / denom)

    return close.rolling(slope_window).apply(_slope, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    entropy_window: int = 30,
    embed_tolerance: float = 0.20,
    entropy_threshold: float = 0.5,
    slope_window: int = 20,
    baseline_ema_span: int = 20,
    max_hold_days: int = 20,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series.

    Long entry on a fresh Approximate Entropy down-cross through
    entropy_threshold, confirmed by a positive regression slope AND
    close > baseline EMA. Exit on close crossing back below the baseline
    EMA, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    apen = _rolling_apen_of_zscored_close(close, entropy_window, m=2, embed_tolerance=embed_tolerance)
    apen_prev = apen.shift(1)
    entropy_collapse = (apen_prev >= entropy_threshold) & (apen < entropy_threshold)

    slope = _rolling_slope(close, slope_window)
    baseline_ema = close.ewm(span=baseline_ema_span, adjust=False).mean()

    direction_confirmed = (slope > 0) & (close > baseline_ema)
    entry = (entropy_collapse.fillna(False)) & (direction_confirmed.fillna(False))
    exit_baseline_break = close < baseline_ema

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_baseline_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
