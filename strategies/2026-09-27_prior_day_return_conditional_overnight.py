"""Strategy: Prior-Day-Return-Conditional Overnight Hold.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per github.com/NafizNoor1/overnight-anomaly's README (Stage 4, "When is the
overnight return biggest?"): bucketing the overnight return (close[t] ->
open[t+1]) by *today's* close-to-close move shows the overnight premium
averages ~8bps after down days, decaying monotonically to -7.4bps after
>2% up days -- "a short-horizon reversal layered on the base [overnight]
effect". This is distinct from every other overnight-holding strategy
already in this repo's knowledge base:
  - 2026-09-18_3day_down_overnight_reversal.py uses a *3-consecutive-close*
    DOWN STREAK trigger (binary streak count), not a single day's return
    magnitude.
  - 2026-09-20_overnight_drift_intraday_weakness_filter.py filters on the
    rolling SUM of the trailing 5 days' INTRADAY-ONLY (open-to-close) log
    returns, not a single day's full close-to-close return.
  - 2026-09-17_5day_low_open_overnight_reversal.py triggers on the day's
    OPEN being a 5-day low + a same-day bullish close, not a lagged
    close-to-close return magnitude at all.

This strategy instead uses TODAY's own close-to-close return (which
includes both the overnight and intraday legs) as a single-day continuous
conditioning variable, and tiers the NEXT overnight hold's exposure into
three states per the source's own disclosed decay pattern: full exposure
after a down day, zero exposure after a big up day (>up_thresh), and a
reduced baseline exposure otherwise -- directly operationalizing "hold big
after weakness, skip after strength" rather than a single binary trigger.

Signal logic
------------
- daily_ret(t) = close(t) / close(t-1) - 1   (full close-to-close return)
- exposure(t+1) [tier for the overnight hold that starts at close(t)]:
    = full_exposure   if daily_ret(t) <  down_thresh   (down day)
    = 0.0             if daily_ret(t) >  up_thresh     (big up day)
    = base_exposure   otherwise                        (mild/flat day)
- Realized return on day t+1 = exposure(t+1) * overnight_ret(t+1), where
  overnight_ret(t+1) = open(t+1)/close(t) - 1.
- Long-only, no leverage beyond full_exposure<=1.0 (SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (exposure in [0,1])
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    down_thresh: float = 0.0,
    up_thresh: float = 0.02,
    full_exposure: float = 1.0,
    base_exposure: float = 0.5,
) -> pd.Series:
    """Return a continuous [0, full_exposure] exposure series.

    exposure.iloc[i] represents the size of the overnight position HELD
    INTO bar i (i.e. entered at close(i-1), realized as bar i's overnight
    return), conditioned on bar (i-1)'s own close-to-close return tier.
    """
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()

    tier = pd.Series(base_exposure, index=close.index, dtype=float)
    tier[daily_ret < down_thresh] = full_exposure
    tier[daily_ret > up_thresh] = 0.0
    tier = tier.fillna(0.0)

    # Decision made at close(i-1) using daily_ret up to (i-1); realized as
    # bar i's overnight return -> shift forward by one bar.
    exposure = tier.shift(1).fillna(0.0)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    down_thresh: float = 0.0,
    up_thresh: float = 0.02,
    full_exposure: float = 1.0,
    base_exposure: float = 0.5,
) -> pd.Series:
    """Overnight (close[i-1] -> open[i]) returns, scaled by the tiered
    exposure from generate_signals.
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    exposure = generate_signals(
        price_df,
        down_thresh=down_thresh,
        up_thresh=up_thresh,
        full_exposure=full_exposure,
        base_exposure=base_exposure,
    )

    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = exposure * overnight_ret
    return strategy_ret.fillna(0.0)
