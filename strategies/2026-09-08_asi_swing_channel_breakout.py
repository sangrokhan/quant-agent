"""Strategy: ASI swing-high/low breakout (donchian-style breakout applied to
the ASI line, not to price).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-026):
Per GoCharting's "Accumulative Swing Index: Trend Confirmation Strategy"
(https://gocharting.com/blog/accumulative-swing-index-trend-confirmation-strategy,
full page inaccessible -- Access Denied -- but the concrete rule is
disclosed verbatim in the Google search-result snippet): "Enter long when
ASI breaks above a prior swing high, confirming trend continuation. Exit
when ASI breaks below a prior swing low." This treats the ASI (Wilder's
Accumulative Swing Index, a cumulative running sum of Swing Index values)
itself as a "price" series and applies a classic Donchian-channel breakout
logic to it directly, rather than the already-tested zero-line-cross rule
(2026-09-06-131 / strategies/2026-09-06_asi_zeroline_cross.py, rejected
decisively 0/216) which fires far more often on every zero-crossing noise
event. Requiring ASI to clear its own N-bar rolling high/low is a much
stricter, less noise-prone confirmation of a genuine swing in trend
strength, per the source's own stated rationale ("confirming trend
continuation").

Swing Index / ASI formula reused verbatim from
strategies/2026-09-06_asi_zeroline_cross.py (Wilder, "New Concepts in
Technical Trading Systems", 1978) -- see that file's docstring for the
full R-selection derivation. This strategy differs ONLY in the signal
logic layered on top of the same ASI series: Donchian-style breakout of
the ASI's own rolling high/low channel, instead of a zero-line cross.

Signal logic
------------
- Compute raw ASI (cumulative sum of the Swing Index).
- Rolling `channel_window`-bar highest/lowest of the ASI series itself
  (Donchian channel on ASI, not price), computed on ASI values EXCLUDING
  the current bar (shifted by 1) to avoid using the current bar's own
  high/low against itself.
- Long entry: ASI closes above its own prior `channel_window`-bar rolling
  high (breakout).
- Exit: ASI closes below its own prior `channel_window`-bar rolling low,
  OR a `max_hold_days` time-stop (added for robustness, not in source).
- Flat otherwise; long-only, matching repo convention.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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


def _swing_index(df: pd.DataFrame, limit_move: float) -> pd.Series:
    """Wilder's Swing Index (SI), classic formulation (reused verbatim
    from strategies/2026-09-06_asi_zeroline_cross.py)."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    c_prev = c.shift(1)
    o_prev = o.shift(1)

    hc = (h - c_prev).abs()
    lc = (l - c_prev).abs()
    hl = (h - l).abs()
    ho_prev = (h - o_prev).abs()
    lo_prev = (l - o_prev).abs()

    k = pd.concat([hc, lc], axis=1).max(axis=1)

    cond1 = (hc >= lc) & (hc >= hl)
    cond2 = (lc >= hc) & (lc >= hl)
    r = pd.Series(np.nan, index=df.index)
    r = r.where(~cond1, hc - 0.5 * lc + 0.25 * ho_prev)
    r = r.where(~(cond2 & ~cond1), lc - 0.5 * hc + 0.25 * lo_prev)
    fallback = hl + 0.25 * (c_prev - o_prev).abs()
    r = r.where(cond1 | cond2, fallback)
    r = r.replace(0, np.nan)

    num = (c - c_prev) + 0.5 * (c - o) + 0.25 * (c_prev - o_prev)
    si = 50.0 * (num / r) * (k / limit_move)
    return si.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    limit_move: float = 3.0,
    channel_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    si = _swing_index(df, limit_move=limit_move)
    asi = si.cumsum()

    prior_high = asi.shift(1).rolling(channel_window, min_periods=channel_window).max()
    prior_low = asi.shift(1).rolling(channel_window, min_periods=channel_window).min()

    entry = asi > prior_high
    exit_break = asi < prior_low

    valid = prior_high.notna() & prior_low.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
