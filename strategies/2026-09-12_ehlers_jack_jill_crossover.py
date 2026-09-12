"""Strategy: Ehlers Jack & Jill adaptive/contra-adaptive SuperSmoother crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-189):
Per John F. Ehlers' "The Jack & Jill Indicator" (MESA Software technical
paper, 2025, http://www.mesasoftware.com/papers/The%20Jack%20and%20Jill%20
Indicator.pdf): fully disclosed EasyLanguage formula for two SuperSmoother
lines built from the SAME base period0 but adapted in OPPOSITE directions
by the same volatility signal:

  - "Jack": adaptive SuperSmoother whose period SHRINKS as its own 1-bar
    ROC (normalized to its 81-bar RMS, clipped to 2 std) rises --
    JackPeriod = period0*(1 - 0.5*JackROC)^2, floored at 2. Jack closely
    tracks price (low lag in volatile/trending moves).
  - "Jill": contra-adaptive SuperSmoother whose period WIDENS as its own
    ROC rises -- JillPeriod = period0*(1 + 0.5*JillROC)^2. Jill is
    deliberately slow and "virtually devoid of cyclic information",
    tracking only the underlying trend.
  - Source's own rule: "when Jack is above Jill going up the hill the
    market trend is up... when Jack is below Jill falling down the hill
    the market trend is down." Separation (Jack-Jill) magnitude = trend
    strength.

Operationalized as a long-only trend-following crossover: long when
Jack > Jill (uptrend per source's literal rule), flat when Jack <= Jill.
No separate strength/magnitude filter in the base version (kept for grid
sensitivity testing via `period0` only, per the source's own single
tunable input).

Economic rationale (source's own): unlike a fixed-period SuperSmoother
crossover (already tested in this repo, e.g. 2026-09-10-021 SuperSmoother
slope+price-position, and the standalone Adaptive SuperSmoother crossover
2026-09-12-146 which uses ONE adaptively-shrinking smoother crossed with
price itself and was REJECTED), Jack & Jill uses TWO smoothers built from
the identical volatility-adaptation signal but pointed in opposite
directions -- this produces a genuinely different lead/lag relationship
(both react to the same regime shift, but diverge rather than converge),
distinct from a single-adaptive-line-vs-price or fixed-vs-fixed crossover.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    period0   (base SuperSmoother period, default 20, source's example).
    rms_window (window for the ROC-normalizing RMS, default 81, source's
        literal value).
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


def _jack_jill(close: pd.Series, period0: float, rms_window: int):
    """Compute Jack (adaptive) and Jill (contra-adaptive) SuperSmoother lines.

    Both lines start with period0 and re-derive their own next-bar period
    from their own ROC (normalized by rolling RMS of that ROC), per the
    source's literal EasyLanguage formula. Implemented as a sequential
    recursive loop since the period itself is state-dependent (adaptive
    filter, not vectorizable directly).
    """
    vals = close.to_numpy(dtype=float)
    m = len(vals)

    jack = np.zeros(m)
    jill = np.zeros(m)
    jack_period = np.full(m, float(period0))
    jill_period = np.full(m, float(period0))

    # rolling buffers of the ROC series for RMS normalization
    jack_roc_hist = []
    jill_roc_hist = []

    for t in range(m):
        p = vals[t]
        if t < 4:
            jack[t] = p
            jill[t] = p
            jack_roc_hist.append(0.0)
            jill_roc_hist.append(0.0)
            continue

        # Jack: adaptive SuperSmoother using jack_period[t] (set by previous bar)
        a0 = (1 - _std_c1(jack_period[t]) + _std_c2(jack_period[t])) / 2.0
        jack[t] = (
            a0 * (p + vals[t - 1])
            + _std_c1(jack_period[t]) * jack[t - 1]
            - _std_c2(jack_period[t]) * jack[t - 2]
        )

        # Jill: contra-adaptive SuperSmoother using jill_period[t]
        a0j = (1 - _std_c1(jill_period[t]) + _std_c2(jill_period[t])) / 2.0
        jill[t] = (
            a0j * (p + vals[t - 1])
            + _std_c1(jill_period[t]) * jill[t - 1]
            - _std_c2(jill_period[t]) * jill[t - 2]
        )

        jack_roc = jack[t] - jack[t - 1]
        jill_roc = jill[t] - jill[t - 1]
        jack_roc_hist.append(jack_roc)
        jill_roc_hist.append(jill_roc)

        window_j = jack_roc_hist[-rms_window:]
        window_i = jill_roc_hist[-rms_window:]
        jack_rms = np.sqrt(np.mean(np.square(window_j))) if window_j else 0.0
        jill_rms = np.sqrt(np.mean(np.square(window_i))) if window_i else 0.0

        jack_roc_norm = min(abs(jack_roc / jack_rms), 2.0) if jack_rms != 0 else 0.0
        jill_roc_norm = min(abs(jill_roc / jill_rms), 2.0) if jill_rms != 0 else 0.0

        if t + 1 < m:
            jack_period[t + 1] = max(period0 * (1 - 0.5 * jack_roc_norm) ** 2, 2.0)
            jill_period[t + 1] = period0 * (1 + 0.5 * jill_roc_norm) ** 2

    return (
        pd.Series(jack, index=close.index),
        pd.Series(jill, index=close.index),
    )


def _std_c1(period: float) -> float:
    period = max(period, 2.0)
    q = np.exp(-1.414 * np.pi / period)
    return 2 * q * np.cos(1.414 * np.pi / period)


def _std_c2(period: float) -> float:
    period = max(period, 2.0)
    q = np.exp(-1.414 * np.pi / period)
    return q * q


def generate_signals(
    price_df: pd.DataFrame,
    period0: float = 20,
    rms_window: int = 81,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    jack, jill = _jack_jill(close, period0=period0, rms_window=rms_window)

    position = (jack > jill).astype(int)
    # Warm-up: no signal for the first few bars (matches source's CurrentBar>=4 guard).
    position.iloc[:5] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period0: float = 20,
    rms_window: int = 81,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, period0=period0, rms_window=rms_window)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
