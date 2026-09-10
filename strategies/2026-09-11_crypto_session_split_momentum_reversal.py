"""Strategy: Session-split (daytime/overnight) lagged momentum/reversal on
crypto hourly bars, per Wu & Pinsky (2026) JRFM paper.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Wu, Z. & Pinsky, E. (2026), "On the Performance of Lagged Momentum and
Reversal Strategies Across Daytime and Overnight Sessions in Bitcoin and
Ethereum Cryptocurrencies", J. Risk Financ. Manag. 19(9), 692
(https://www.mdpi.com/1911-8074/19/9/692, visited this iteration via
browser_exec fallback after web_search returned only listing snippets):
splitting the 24h crypto trading day into two complementary 12h sessions
(a "night" session starting at some UTC hour, and the complementary "day"
session 12h later) and applying independent momentum/reversal rules to each
session (position for the CURRENT session is set by the SIGN of the LAGGED
return of the SAME session type, i.e. "conditional continuation/reversal"
not a raw calendar effect) reveals return predictability not visible in
daily returns. The paper's own full-sample optimum: BTC = Reversal/Reversal
with the daytime session starting at 08:00 UTC; ETH = Long/Reversal with the
daytime session starting at 05:00 UTC (i.e. ETH's night session, 05:00-17:00
UTC, is held unconditionally Long, while its day session, 17:00-05:00 UTC,
uses a Reversal rule keyed off the previous day session's own return).

The paper's own conclusion is important context for grounding this test:
these full-sample-selected rules do NOT survive a chronological 2016-2020
train / 2021-2025 holdout for BTC (BTC's selected rule underperforms
buy-and-hold out-of-sample), and neither difference is statistically
significant after Hansen's Superior Predictive Ability test accounting for
the 300-combination search. Only the ETH rule persists in the holdout. This
strategy implements the ETH rule (the paper's own more-robust finding) as
the primary candidate, with the BTC rule available via `night_rule`/
`day_rule` params for a documented robustness/falsification comparison.

First session-split (sub-daily lagged momentum/reversal) strategy in this
repo -- distinct from all prior hour-of-day (rejected, unstable year-to-year
per a separate source) and day-of-week calendar strategies, since here the
position depends on the LAGGED RETURN of the same session type (a genuine
conditional continuation/reversal signal), not an unconditional calendar
effect.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({-1,0,1} position;
        note this repo's other strategies use {0,1} long/flat, but the
        paper's own rules are long/short/cash {-1,0,1} -- SAFETY.md permits
        backtested short positions, only real order placement is banned)
    generate_returns(price_df, **params) -> pd.Series  (daily/hourly
        strategy returns, resampled to daily via compounding for the
        grid/validator harness which assumes ~daily-bar Sharpe annotation)

Requires HOURLY price_df (as returned by data/loaders.py's load_crypto with
its default interval="1h"); on daily-bar data (e.g. equity via load_equity)
there is only one bar per UTC day so no sub-daily session split is possible
-- generate_signals returns an all-flat/no-trade series in that case (an
expected "not applicable" result for the falsification check on equities).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_RULES = {"cash", "long", "short", "momentum", "reversal"}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_hourly(df: pd.DataFrame) -> bool:
    if len(df) < 3:
        return False
    hours = pd.Series(df.index).dt.hour
    return hours.nunique() > 1


def _session_id_and_leg(index: pd.DatetimeIndex, session_start_hour: int) -> tuple:
    """For each timestamp, compute which 12h session "leg" it belongs to
    (0 = the leg starting at session_start_hour, 1 = the leg starting
    session_start_hour+12) and a monotonically increasing session sequence
    number (unique per 12h block) for grouping/lag purposes."""
    hours = index.hour + index.minute / 60.0
    rel = (hours - session_start_hour) % 24
    leg = (rel >= 12).astype(int)  # 0 for first 12h (session_start_hour..+12), 1 for second half

    # Session sequence number: increments every 12h. Use integer division of
    # hours-since-epoch-adjusted-by-offset.
    total_hours = (index - index[0]).total_seconds() / 3600.0
    offset_hours = (index[0].hour + index[0].minute / 60.0 - session_start_hour) % 24
    seq = np.floor((total_hours + offset_hours) / 12.0).astype(int)
    return seq, leg


def _rule_position(rule: str, lagged_return: pd.Series) -> pd.Series:
    if rule == "cash":
        return pd.Series(0.0, index=lagged_return.index)
    if rule == "long":
        return pd.Series(1.0, index=lagged_return.index)
    if rule == "short":
        return pd.Series(-1.0, index=lagged_return.index)
    if rule == "momentum":
        return np.sign(lagged_return).fillna(0.0)
    if rule == "reversal":
        return -np.sign(lagged_return).fillna(0.0)
    raise ValueError(f"unknown rule: {rule}")


def generate_signals(
    price_df: pd.DataFrame,
    session_start_hour: int = 5,
    night_rule: str = "long",
    day_rule: str = "reversal",
) -> pd.Series:
    """Return a {-1,0,1} position series, held constant within each 12h
    session and determined by `night_rule`/`day_rule` applied to the SAME
    session type's PRECEDING realized return (per Wu & Pinsky Eq. 5)."""
    assert night_rule in _RULES and day_rule in _RULES

    df = _prep(price_df)
    close = df["close"]

    if not _is_hourly(df):
        # Daily-bar (equity) data: sub-daily session split not meaningful.
        return pd.Series(0, index=close.index, dtype=int).rename("position")

    seq, leg = _session_id_and_leg(df.index, session_start_hour)
    seq = pd.Series(seq, index=df.index)
    leg = pd.Series(leg, index=df.index)

    # Per-session realized return: last close / first close of that session,
    # computed once per session then broadcast back to every bar in it.
    session_df = pd.DataFrame({"seq": seq, "leg": leg, "close": close})
    session_ret = session_df.groupby("seq")["close"].apply(lambda s: s.iloc[-1] / s.iloc[0] - 1.0 if len(s) > 0 else np.nan)
    session_leg = session_df.groupby("seq")["leg"].first()

    # For each session sequence number, the "same session type" two seq-steps
    # back (12h * 2 = 24h earlier) gives the natural lag used by the paper
    # (lagged return of the SAME session type -- night depends on prior
    # night, day depends on prior day).
    lagged_ret_by_seq = session_ret.shift(2)

    position_by_seq = pd.Series(0.0, index=session_ret.index)
    night_mask = session_leg == 0
    day_mask = session_leg == 1
    position_by_seq[night_mask] = _rule_position(night_rule, lagged_ret_by_seq[night_mask])
    position_by_seq[day_mask] = _rule_position(day_rule, lagged_ret_by_seq[day_mask])

    position = seq.map(position_by_seq).fillna(0.0)
    position.index = df.index
    return position.rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    session_start_hour: int = 5,
    night_rule: str = "long",
    day_rule: str = "reversal",
) -> pd.Series:
    """Returns DAILY-compounded strategy returns (even though signals/data
    are hourly) so downstream validators (which hardcode freq='D'
    annualization -- see validation/validators.py check_sharpe_ratio) get a
    correctly-scaled Sharpe, matching the pattern used by this repo's other
    hourly-bar crypto strategies (e.g. 2026-09-04_crypto_orb_first_hour_breakout.py).
    Position is shifted by one bar to avoid look-ahead."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        session_start_hour=session_start_hour,
        night_rule=night_rule,
        day_rule=day_rule,
    )
    bar_ret = close.pct_change().fillna(0.0)
    strat_bar_ret = bar_ret * position.shift(1).fillna(0)

    if not _is_hourly(df):
        return strat_bar_ret.rename("returns")

    daily_ret = (1.0 + strat_bar_ret).groupby(df.index.normalize()).prod() - 1.0
    daily_ret.index = pd.to_datetime(daily_ret.index)
    return daily_ret.rename("returns")
