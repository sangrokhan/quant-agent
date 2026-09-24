"""Strategy: Bulkowski Dead-Cat-Bounce Setup -- delayed entry, fixed-day exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-132):
Per https://thepatternsite.com/DCBSetup.html (Thomas Bulkowski, browser_exec),
a large single-day price decline ("event day") is often followed, days to
weeks later, by a tradable recovery. Bulkowski's own 2009 study ($10,000 per
position, $20 round-trip commission + SEC fee, no slippage) found: entering
at the LOW PRICE reached N days after the event day (buying only if price
actually revisits that low), then exiting a FIXED number of trading days
later, produced its best average per-trade profit ($364.46, 53% win rate,
1,074 samples) at entry_offset=7 days post-event, exit after 42 trading
days. This is distinct from every dead-cat-bounce SHORT-the-fade strategy
already tested in this repo (2026-09-24-093) and from the mean-reversion
"Adjusted Failed Bounce" IBS strategy (2026-09-05-019) -- this is a delayed
LONG entry with a fixed-day (not signal-based) exit, betting on eventual
recovery well after the initial crash, not a fade of the immediate bounce.

Adaptation for this repo's daily-close-only OHLCV contract: rather than a
literal "buy if price revisits the entry-day's low" contingent order (which
needs intraday low tracking against a moving target), this implementation
uses the CLOSE price entry_offset trading days after the event day as the
entry price (a reasonable mechanical simplification preserving the delayed-
entry economics), holding for exit_hold_days trading days, then exiting
unconditionally (fixed-day exit, matching the source's own methodology of
testing exits "1 to 44 trading days later").

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 long/flat)
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
    event_decline_pct: float = 0.10,
    entry_offset_days: int = 7,
    exit_hold_days: int = 42,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    event_decline_pct : minimum single-day close-to-close decline (as a
        positive fraction, e.g. 0.10 = -10%) that defines an "event day".
    entry_offset_days : number of trading days after the event day at which
        entry occurs (at that day's close).
    exit_hold_days : fixed number of trading days held before exit
        (unconditional time-based exit, no signal-based exit).
    """
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    daily_ret = close.pct_change()
    is_event_day = daily_ret <= -event_decline_pct

    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_idx = -1
    # Track scheduled entries: event_day_idx -> planned entry_idx
    event_indices = [i for i in range(n) if bool(is_event_day.iloc[i])]

    scheduled_entries = set()
    for ev_i in event_indices:
        entry_i = ev_i + entry_offset_days
        if entry_i < n:
            scheduled_entries.add(entry_i)

    for i in range(n):
        if not in_position and i in scheduled_entries:
            in_position = True
            entry_idx = i

        if in_position:
            held_days = i - entry_idx
            if held_days >= exit_hold_days:
                in_position = False

        position.iloc[i] = 1 if in_position else 0

    return position.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    event_decline_pct: float = 0.10,
    entry_offset_days: int = 7,
    exit_hold_days: int = 42,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    positions = generate_signals(
        price_df,
        event_decline_pct=event_decline_pct,
        entry_offset_days=entry_offset_days,
        exit_hold_days=exit_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = positions.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
