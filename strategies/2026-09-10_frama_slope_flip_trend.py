"""Strategy: Fractal Adaptive Moving Average (FRAMA) slope-flip trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per thefintechbuilder.com's FRAMA formula guide (John Ehlers' original
indicator, cross-referenced against forexmt4indicators.com's FRAMA
calculator): FRAMA is an adaptive EMA whose smoothing factor (alpha) is
derived from the price series' fractal dimension D over a rolling window
(D = (log(N1+N2) - log(N3)) / log(2), where N1/N2/N3 are normalized
high-low ranges over the first half, second half, and full lookback window
respectively), then alpha = clip(exp(-4.6*(D-1)), alpha_min, 1). A low
fractal dimension (smooth, trending price) yields a HIGH alpha (fast,
responsive line); a high fractal dimension (choppy, noisy price) yields a
LOW alpha (heavy smoothing) -- the line self-adjusts its responsiveness to
the market's own roughness, unlike KAMA's efficiency-ratio-based adaptive
smoothing (already tested in this repo, id 2026-09-04-151) which uses a
directional-efficiency measure rather than a fractal-dimension/roughness
measure. First FRAMA strategy in this repo (0 prior entries).

Signal logic
------------
- Entry (long): FRAMA slope turns positive (FRAMA[t] > FRAMA[t-1] after
  FRAMA[t-1] <= FRAMA[t-2]) AND close > FRAMA[t] (price above the adaptive
  line, confirming the slope-flip is a genuine trend start, not noise).
- Exit: FRAMA slope turns negative (FRAMA[t] < FRAMA[t-1]), or close falls
  below FRAMA, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _frama(df: pd.DataFrame, window: int, alpha_min: float) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    n = window
    half = n // 2

    frama = pd.Series(index=df.index, dtype=float)
    prev = None

    highs = high.values
    lows = low.values
    closes = close.values

    for i in range(len(df.index)):
        if i < n - 1:
            frama.iloc[i] = float("nan")
            continue

        window_high = highs[i - n + 1 : i + 1]
        window_low = lows[i - n + 1 : i + 1]

        h1, l1 = window_high[:half], window_low[:half]
        h2, l2 = window_high[half:], window_low[half:]

        n1 = (h1.max() - l1.min()) / half if half > 0 else 0.0
        n2 = (h2.max() - l2.min()) / (n - half) if (n - half) > 0 else 0.0
        n3 = (window_high.max() - window_low.min()) / n

        if n1 <= 0 or n2 <= 0 or n3 <= 0:
            d = 1.0
        else:
            d = (math.log(n1 + n2) - math.log(n3)) / math.log(2)

        alpha = math.exp(-4.6 * (d - 1))
        alpha = max(alpha_min, min(alpha, 1.0))

        price_t = closes[i]
        if prev is None:
            prev = price_t
        prev = alpha * price_t + (1 - alpha) * prev
        frama.iloc[i] = prev

    return frama


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 16,
    alpha_min: float = 0.01,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    frama = _frama(df, window, alpha_min)

    slope_up = (frama > frama.shift(1)) & (frama.shift(1) <= frama.shift(2))
    slope_down = frama < frama.shift(1)
    above_frama = close > frama

    valid = frama.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if slope_down.iloc[i] or (not above_frama.iloc[i]) or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if slope_up.iloc[i] and above_frama.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 16,
    alpha_min: float = 0.01,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df, window=window, alpha_min=alpha_min, max_hold_days=max_hold_days
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
