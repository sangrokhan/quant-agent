"""Strategy: ADR-Relative Gap Classification + Continuation (daily-bar adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per LuxAlgo's "Gap Rules Interaction" indicator
(https://www.luxalgo.com/library/indicator/gap-rules-interaction, read via
browser_exec after web_search DDGS backend returned "No results found" for
this iteration's queries), each session's opening gap is sized against a
rolling Average Daily Range (ADR) baseline and classified into three
regimes rather than treated uniformly:

- "Negligible": |gap| < negligible_frac * ADR -- no playbook, stay flat.
- "Inside prior range" (gap smaller than ADR but non-negligible): source
  treats this as ambiguous/no strong edge -- stay flat here too (this repo
  simplifies the source's richer opening-range-lock-in logic, which needs
  intraday bars we don't have, down to the two directionally decisive
  regimes below).
- "Beyond ADR" (|gap| >= beyond_frac * ADR): source's "continuation
  alignment" (gap-and-go) calls for trading WITH the gap direction when
  the day's own trading holds the gap side rather than round-tripping back
  through the prior close (source's "fill and negation" case, the
  opposite outcome). On daily bars (no intraday opening-range confirmation
  available) this is approximated as: enter at today's close in the gap
  direction, conditioned on the close NOT having round-tripped back through
  the prior close intraday (i.e., low/high did not re-cross prior_close
  against the gap direction), exit after a fixed max_hold_days or on the
  first close back through the prior close (negation).

This is distinct from every other gap strategy in this repo:
- 2026-09-16-079 (rejected): single unconditional gap-fade threshold, no
  ADR-relative sizing, no continuation regime.
- 2026-09-20 overnight_gap_dual_classification (id 2026-09-20-XXX): also a
  fill/go dual-classification, but sizes the gap by a FIXED percentage
  threshold and a VOLUME-ratio filter, not by ADR-relative sizing, and has
  no "negation" exit rule tied to the prior close. This strategy uses
  ADR(N)-relative gap sizing (the source's actual mechanism) and a
  fill/negation exit condition instead of a volume filter, so the
  triggering condition and exit logic are both mechanically different.

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
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    adr_window: int = 10,
    negligible_frac: float = 0.1,
    beyond_frac: float = 1.0,
    max_hold_days: int = 3,
) -> pd.Series:
    """Return a {-1, 0, 1} short/flat/long position series."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prior_close = close.shift(1)
    daily_range = (high - low)
    adr = daily_range.shift(1).rolling(adr_window).mean()

    gap = open_ - prior_close
    gap_dir = np.sign(gap)
    gap_abs_over_adr = gap.abs() / adr

    beyond = gap_abs_over_adr >= beyond_frac
    negligible = gap_abs_over_adr < negligible_frac

    # "Holds the gap side": today's own low (for up-gaps) / high (for
    # down-gaps) does not re-cross back through prior_close intraday.
    holds_up = low > prior_close
    holds_down = high < prior_close

    entry_up = beyond & (gap_dir > 0) & holds_up
    entry_down = beyond & (gap_dir < 0) & holds_down

    entry = pd.Series(0, index=close.index, dtype=int)
    entry[entry_up.fillna(False)] = 1
    entry[entry_down.fillna(False)] = -1

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    direction = 0
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            # Negation: a close back through the prior close cancels the
            # continuation thesis.
            negated = (
                (direction == 1 and close.iloc[i] < prior_close.iloc[i])
                or (direction == -1 and close.iloc[i] > prior_close.iloc[i])
            ) if pd.notna(prior_close.iloc[i]) else False
            if negated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = direction
        else:
            sig = entry.iloc[i]
            neg_ok = (not bool(negligible.iloc[i])) if pd.notna(negligible.iloc[i]) else False
            if sig != 0 and neg_ok:
                in_position = True
                direction = int(sig)
                entry_idx = i
                position.iloc[i] = direction
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
