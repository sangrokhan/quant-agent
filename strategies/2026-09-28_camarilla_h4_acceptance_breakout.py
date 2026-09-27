"""Strategy: Camarilla H4 breakout-with-acceptance (long-only, daily bars).

Hypothesis (source: https://arongroups.co/forex-articles/camarilla-pivot-trading-strategy/,
read 2026-09-28 via browser_exec after this iteration's web_search for the
Camarilla query returned results directly; Cup and Handle/NR7/Head-and-
Shoulders/SuperTrend novelty checks this iteration all found saturated
prior coverage before landing on this angle):

Camarilla pivot levels (Nick Scott, 1989) derive 4 resistance levels
(H1-H4) and 4 support levels (L1-L4) from the PRIOR day's close and H-L
range, using a fixed 1.1-based multiplier ladder:
    H1 = C + Range*(1.1/12)   L1 = C - Range*(1.1/12)
    H2 = C + Range*(1.1/6)    L2 = C - Range*(1.1/6)
    H3 = C + Range*(1.1/4)    L3 = C - Range*(1.1/4)
    H4 = C + Range*(1.1/2)    L4 = C - Range*(1.1/2)
where Range = prior day's High - Low, C = prior day's Close.

Source's own disclosed breakout rule (distinct from this repo's existing
Camarilla entry, id=2026-09-04-119, which trades the H3/L3 MEAN-REVERSION
zone): H4/L4 are the "structural extremes" -- source explicitly warns
against entering on the first spike through H4 ("that's where traps
live") and instead requires "acceptance" -- a CLOSE beyond H4 (not an
intrabar touch/snap-back) -- as the valid breakout trigger, since Camarilla
was designed with a reversion-inside/breakout-outside framing where H4/L4
crossings with genuine follow-through indicate real momentum. This is a
trend-following breakout construction, the deliberate mirror-opposite use
of the same indicator from the already-tested mean-reversion entry.

First Camarilla-H4-acceptance-breakout variant in this repo (prior entry
tested only the H3/S3 reversion zone; this tests the H4 "structural
extreme" breakout side with a close-confirmation rule, as the source
explicitly frames these as two distinct, complementary playbooks of the
same indicator).

Signal logic
------------
- Camarilla levels computed daily from the PRIOR bar's close/high/low
  (shifted by 1, so no lookahead).
- Entry (long): today's close > yesterday's H4 level (breakout with
  "acceptance" == confirmed by a full-bar close beyond the level, not an
  intrabar touch) AND yesterday's close was NOT already above yesterday's
  H4 (fresh breakout, not already extended).
- Stop-loss: the breakout bar's own H3 level (a level below H4, giving the
  breakout room but exiting if it fails and falls back below the "with-
  trend trigger zone" into the reversion-only zone) -- computed from the
  SAME prior-day base as the entry's H4, consistent construction.
- Target: entry + reward_r_multiple * (entry - stop) (repo convention,
  since source's own "opposite band" target isn't crisply computable
  without intraday data).
- Time-stop: max_hold_days safety exit (source doesn't disclose one).
- Long-only, one position at a time.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _camarilla_levels(df: pd.DataFrame):
    """Compute H3/H4 levels from the PRIOR bar's close/high/low (shift 1)."""
    prior_close = df["close"].shift(1)
    prior_range = (df["high"] - df["low"]).shift(1)
    h3 = prior_close + prior_range * (1.1 / 4)
    h4 = prior_close + prior_range * (1.1 / 2)
    return h3, h4


def _compute_trades(
    df: pd.DataFrame,
    reward_r_multiple: float,
    max_hold_days: int,
):
    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    h3, h4 = _camarilla_levels(df)
    h3 = h3.to_numpy()
    h4 = h4.to_numpy()
    n = len(df)

    trades = []
    i = 1
    while i < n:
        if np.isnan(h4[i]) or np.isnan(h4[i - 1]):
            i += 1
            continue
        fresh_breakout = close[i] > h4[i] and not (close[i - 1] > h4[i - 1])
        if fresh_breakout:
            entry_idx = i
            entry_price = close[i]
            stop_price = h3[i]
            risk = entry_price - stop_price
            if risk <= 0 or np.isnan(stop_price):
                i += 1
                continue
            target_price = entry_price + reward_r_multiple * risk

            exit_idx = None
            exit_price = None
            for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                if low[k] <= stop_price:
                    exit_idx = k
                    exit_price = stop_price
                    break
                if high[k] >= target_price:
                    exit_idx = k
                    exit_price = target_price
                    break
            if exit_idx is None:
                exit_idx = min(entry_idx + max_hold_days, n - 1)
                exit_price = close[exit_idx]

            trades.append((entry_idx, exit_idx, entry_price, exit_price))
            i = exit_idx + 1
        else:
            i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(df, reward_r_multiple, max_hold_days)
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_trades(df, reward_r_multiple, max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = pd.Series(0.0, index=df.index)

    for entry_idx, exit_idx, entry_price, exit_price in trades:
        if exit_idx > entry_idx:
            strat_ret.iloc[entry_idx + 1 : exit_idx + 1] = daily_ret.iloc[
                entry_idx + 1 : exit_idx + 1
            ]
        exit_close = df["close"].iloc[exit_idx]
        if exit_close != 0 and exit_price != exit_close:
            prior_close = df["close"].iloc[exit_idx - 1] if exit_idx > 0 else df["close"].iloc[exit_idx]
            if prior_close != 0:
                strat_ret.iloc[exit_idx] = (exit_price / prior_close) - 1.0

    return strat_ret
