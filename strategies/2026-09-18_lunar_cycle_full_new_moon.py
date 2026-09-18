"""Strategy: Full Moon / New Moon lunar-cycle seasonal timing (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Yuan, Zheng & Zhu (2006, "Are Investors Moonstruck?") and the
QuantifiedStrategies.com summary/backtest read this iteration, stock (and by
extension crypto, tested here for asset-class breadth) index returns are
systematically lower around full-moon days and higher around new-moon days,
a documented lunar-cycle seasonal anomaly attributed to mood/risk-aversion
effects on aggregate investor behavior. The source's own two variants:
  - "Full Moon Strategy": long from the full-moon date to the next new-moon
    date (source backtest: annual return 4.4%, ~50% time invested, MDD 49%
    on SPY since ~1990s -- source notes outperformance concentrated
    post-2008/09).
  - "New Moon Strategy": long from the new-moon date to the next full-moon
    date (source backtest: annual return 2.8%, MDD 44%).
We implement both as a single switchable `phase_variant` parameter so the
grid test (Step 6) can compare both source-stated variants directly, rather
than picking one arbitrarily.

Moon phase is computed via the standard synodic-month approximation (no
external astronomy library available/needed): a reference exact new-moon
timestamp (2000-01-06 18:14 UTC, well-known reference epoch) plus the mean
synodic period of 29.53058867 days gives each date's moon age in
[0, 29.53058867) days; age near 0 = new moon, age near synodic/2 = full
moon. This is accurate to well within one calendar day over any realistic
backtest window, which is sufficient for a daily-bar equity/crypto signal.

Signal logic
------------
- moon_age = (days since reference new moon) mod synodic_period.
- is_new_moon day: moon_age <= new_moon_window OR moon_age >=
  (synodic_period - new_moon_window) (near 0, wrapping).
- is_full_moon day: |moon_age - synodic_period/2| <= full_moon_window.
- phase_variant="full_to_new": go long on a full-moon day, hold until (and
  including) the day before the next new-moon day, then flat until the next
  full moon.
- phase_variant="new_to_full": go long on a new-moon day, hold until (and
  including) the day before the next full-moon day, then flat until the
  next new moon.
- Flat otherwise (outside any active holding window, e.g. before the first
  trigger date in the sample).

This is a pure calendar/astronomical-timing strategy: no price-derived
indicator, works identically on any daily-bar symbol (equity or crypto)
since it depends only on the DatetimeIndex, not on OHLCV values themselves
(OHLCV is only used to compute daily returns once positioned).

Sources read this iteration:
- https://www.quantifiedstrategies.com/full-moon-moon-phases-lunar-cycles-trading-strategies/
  (backtest summary, both variants' stated annual return/MDD, referencing
  Yuan/Zheng/Zhu 2006 "Are Investors Moonstruck?" academic study).

First lunar-cycle / moon-phase strategy in this repo (zero prior matches for
"moon phase"/"lunar" in strategies_index.jsonl).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd

SYNODIC_PERIOD_DAYS = 29.53058867
# Well-known reference exact new moon: 2000-01-06 18:14 UTC.
REFERENCE_NEW_MOON = pd.Timestamp("2000-01-06 18:14:00", tz="UTC")


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _moon_age_days(index: pd.DatetimeIndex) -> pd.Series:
    """Return moon age in days [0, SYNODIC_PERIOD_DAYS) for each timestamp."""
    idx = index
    if idx.tz is None:
        idx_utc = idx.tz_localize("UTC")
    else:
        idx_utc = idx.tz_convert("UTC")
    delta_days = (idx_utc - REFERENCE_NEW_MOON).total_seconds() / 86400.0
    age = pd.Series(delta_days, index=index) % SYNODIC_PERIOD_DAYS
    return age


def _phase_flags(
    price_df: pd.DataFrame,
    new_moon_window: float,
    full_moon_window: float,
) -> tuple[pd.Series, pd.Series]:
    df = _prep(price_df)
    age = _moon_age_days(df.index)
    half = SYNODIC_PERIOD_DAYS / 2.0
    is_new = (age <= new_moon_window) | (age >= (SYNODIC_PERIOD_DAYS - new_moon_window))
    is_full = (age - half).abs() <= full_moon_window
    return is_new, is_full


def generate_signals(
    price_df: pd.DataFrame,
    phase_variant: str = "full_to_new",
    new_moon_window: float = 1.0,
    full_moon_window: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on lunar-cycle timing."""
    df = _prep(price_df)
    is_new, is_full = _phase_flags(df, new_moon_window, full_moon_window)

    if phase_variant == "full_to_new":
        entry_flag, exit_trigger_flag = is_full, is_new
    elif phase_variant == "new_to_full":
        entry_flag, exit_trigger_flag = is_new, is_full
    else:
        raise ValueError(f"Unknown phase_variant: {phase_variant!r}")

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df.index)):
        if not in_position:
            if entry_flag.iloc[i]:
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            if exit_trigger_flag.iloc[i]:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    phase_variant: str = "full_to_new",
    new_moon_window: float = 1.0,
    full_moon_window: float = 1.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        phase_variant=phase_variant,
        new_moon_window=new_moon_window,
        full_moon_window=full_moon_window,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
