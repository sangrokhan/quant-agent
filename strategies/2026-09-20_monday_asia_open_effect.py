"""Strategy: BTC/ETH "Monday Asia Open Effect" intraday trend window.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/
(Concretum Group, Zarattini/Pagani/Barbon, building on their SSRN paper
"Catching Crypto Trends"): a high-frequency, volatility-targeted long-short
Bitcoin trend-following benchmark shows a pronounced intraweek seasonality
pattern they call the "Monday Asia Open Effect" -- strongly positive
trend-following performance from Sunday ~19:00 New York time through
Monday ~19:00 New York time (aligned with the Tokyo cash equity market's
Monday open), more pronounced in the post-mid-2020 (institutional-adoption)
period; in contrast, US Sunday morning shows weaker/choppier, more
mean-reverting price action. The source's own framing: this is about
*trend-following signal quality* varying by time-of-week, not a passive
buy-and-hold weekend effect (which prior entries in this repo already
tested and rejected, e.g. 2026-09-04-029 unconditional Friday-to-Monday
hold, 2026-09-13-020 weekend-momentum-hold).

Adaptation to a testable single-asset long-only strategy (source used a
long-short vol-targeted multi-model ensemble, not directly reproducible
with this repo's single-indicator interface):
    1. Convert the hourly timestamp index to US Eastern time.
    2. Define the "active window": Sunday >= 19:00 ET through Monday
       23:59 ET (approximating the source's "next ~24 hours into Monday").
    3. Within the active window, take a simple short-term momentum signal
       (close vs close `mom_lookback_hours` ago); go long if positive,
       flat if non-positive or negative (long-only, no short side, to keep
       this consistent with the repo's other daily/hourly strategies).
    4. Outside the active window: flat (no position) -- this isolates
       whether the specific window itself carries the edge, per the
       source's own claim that trend-following quality (not raw returns)
       is concentrated there.
    5. A max_hold_hours time-stop caps how long a position started inside
       the window can be held once the window has passed (default: exit
       promptly at window end rather than carrying the position
       indefinitely).

First "Monday Asia Open Effect" / intraweek trend-following-window
strategy in this repo -- distinct from all prior weekend/day-of-week
seasonality entries which test unconditional buy-and-hold return
seasonality rather than gating a momentum SIGNAL to a specific
sub-24-hour trend-following window.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0, 1})

Note: this strategy is crypto-native (relies on Bitcoin's continuous
24/7 trading and the specific Sunday-evening/Monday session-open
mechanism); it is not expected to transfer to equity (QQQ/SPY), which
have no Sunday trading session at all -- tested on equity anyway per
Step 6's cross-asset-class requirement, with the expectation (stated
here in advance, per the source's own framing) that equity should show
a degenerate/flat result since the active window rarely overlaps equity
trading hours.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _in_active_window(idx: pd.DatetimeIndex) -> pd.Series:
    """Sunday 19:00 ET through Monday 23:59:59 ET."""
    if idx.tz is None:
        idx_et = idx.tz_localize("UTC").tz_convert("America/New_York")
    else:
        idx_et = idx.tz_convert("America/New_York")
    dow = idx_et.dayofweek  # Monday=0 ... Sunday=6
    hour = idx_et.hour
    is_sunday_evening = (dow == 6) & (hour >= 19)
    is_monday = dow == 0
    return pd.Series(is_sunday_evening | is_monday, index=idx)


def generate_signals(
    price_df: pd.DataFrame,
    mom_lookback_hours: int = 6,
    max_hold_hours: int = 30,
) -> pd.Series:
    """Return a {0, 1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    active = _in_active_window(df.index).values
    momentum = close.pct_change(mom_lookback_hours).values
    close_v = close.values

    position = [0] * n
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if (not active[i]) or held >= max_hold_hours:
                in_pos = False
                position[i] = 0
                continue
            position[i] = 1
            continue
        if active[i] and not pd.isna(momentum[i]) and momentum[i] > 0:
            in_pos = True
            entry_idx = i
            position[i] = 1
        else:
            position[i] = 0

    return pd.Series(position, index=df.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted returns at the data's native bar frequency (no
    transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    bar_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * bar_ret
    return strategy_ret
