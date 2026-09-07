"""Strategy: Crypto weekend-range sweep-and-reclaim breakout (daily-bar analog).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-098):
Per https://voiceofchain.com/academy/weekend-crypto-trading-strategy, crypto
weekend liquidity is thin, so price often sweeps a visible weekend range
extreme before reclaiming/rejecting it: "identify Friday close range, wait
for a weekend sweep, enter only after reclaim or rejection." The source's
own mechanics are intraday (15m sweep/reclaim on Sat/Sun), which this
repo's daily-bar crypto loader cannot replicate directly -- adapted here as
a daily-bar analog: define the weekend range as the high/low spanning
Saturday and Sunday's daily bars; if Monday's low dips below (sweeps) that
weekend range low, then Monday's own close reclaims back above the
weekend range LOW (not necessarily the high), that is the daily-bar analog
of a "sweep + reclaim" long trigger.

This is distinct from the already-tested static Friday-close-to-Monday-
close weekend HOLD calendar anomaly (2026-09-04-029, rejected) since that
strategy is an unconditional calendar hold with no price-structure
condition, whereas this strategy is a genuine range-breakout/sweep
mechanism that only triggers on specific weekend price behavior.
Crypto-only by construction (equity markets have no weekend bars).

Signal logic
------------
- Weekend range: for each week, high/low of Saturday+Sunday daily bars.
- Sweep: Monday's low < weekend range low (price dipped below the weekend
  low).
- Reclaim: Monday's close > weekend range low (price closed back above
  that level the same day) -- the daily-bar analog of "reclaim on 15m
  close."
- Entry (long): on Monday's close, if both sweep and reclaim conditions
  are true.
- Exit: close crosses back below the weekend range low (failed reclaim),
  or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series. Crypto-only (needs weekend bars)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    weekday = pd.Series(close.index, index=close.index).apply(lambda ts: pd.Timestamp(ts).weekday())
    iso_year_week = pd.Series(close.index, index=close.index).apply(
        lambda ts: pd.Timestamp(ts).isocalendar()[:2]
    )

    is_weekend = weekday.isin([5, 6])  # Sat=5, Sun=6
    is_monday = weekday == 0

    # Weekend range low/high per (year, week) group over weekend bars only.
    weekend_low_by_week: dict = {}
    weekend_high_by_week: dict = {}
    for i in range(n):
        if bool(is_weekend.iloc[i]):
            key = iso_year_week.iloc[i]
            lo, hi = low.iloc[i], high.iloc[i]
            if key not in weekend_low_by_week:
                weekend_low_by_week[key] = lo
                weekend_high_by_week[key] = hi
            else:
                weekend_low_by_week[key] = min(weekend_low_by_week[key], lo)
                weekend_high_by_week[key] = max(weekend_high_by_week[key], hi)

    entry = pd.Series(False, index=close.index)
    entry_wknd_low: dict = {}
    for i in range(n):
        if bool(is_monday.iloc[i]):
            # Monday belongs to the ISO week that includes the PRECEDING
            # Sat/Sun -- Python isocalendar treats Mon as start of week, so
            # the preceding weekend's key is (this Monday's iso_year, iso_week-1)
            # unless week 1 wraps a year boundary. Approximate by looking at
            # the two calendar days immediately preceding this Monday bar's
            # index position instead (index-based, robust to iso edge cases).
            wknd_low = None
            wknd_high = None
            j = i - 1
            found_weekend = False
            while j >= 0 and bool(is_weekend.iloc[j]):
                lo, hi = low.iloc[j], high.iloc[j]
                wknd_low = lo if wknd_low is None else min(wknd_low, lo)
                wknd_high = hi if wknd_high is None else max(wknd_high, hi)
                found_weekend = True
                j -= 1
            if found_weekend and wknd_low is not None:
                swept = low.iloc[i] < wknd_low
                reclaimed = close.iloc[i] > wknd_low
                if swept and reclaimed:
                    entry.iloc[i] = True
                    entry_wknd_low[i] = wknd_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    active_wknd_low = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            failed = active_wknd_low is not None and close.iloc[i] < active_wknd_low
            if failed or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                active_wknd_low = entry_wknd_low.get(i)
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
