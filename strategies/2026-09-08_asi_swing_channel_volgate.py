"""Strategy: ASI swing-channel breakout + low-vol regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-045):
Direct follow-up to the near-miss ASI swing-channel breakout strategy
already in this repo (id=2026-09-08-026,
strategies/2026-09-08_asi_swing_channel_breakout.py): full-sample Sharpe
0.734 (SPY) / 0.949 (QQQ), both near-misses with MDD/TC/WF all passing.
The grid showed a strong regime concentration: low-vol 12/24 pass,
mid-vol 4/24 pass, high-vol 0/24 pass -- a much cleaner concentration
signature than this session's other two near-miss revisit attempts
(VQI: evenly spread, gate hurt; Garman-Klass: spread across low+mid,
gate helped but not enough), closely matching the KAMA/ATR-band
precedent (2026-09-06-183, edge concentrated 8/16 low-vol vs 1/16
high-vol) that WAS successfully rescued by a low-vol-only gate.

Adds an explicit realized-volatility regime gate (20d realized vol <=
its own trailing 1yr rolling median, identical construction to the
accepted `2026-09-03_bb_meanrev_qqq_volregime.py`) restricting entries
to the low-vol regime only, keeping the base ASI-channel-breakout
entry/exit logic otherwise unchanged.

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


def _low_vol_regime(close: pd.Series, vol_window: int, median_window: int) -> pd.Series:
    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()
    trailing_median = realized_vol.rolling(median_window, min_periods=vol_window).median()
    return (realized_vol <= trailing_median).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    limit_move: float = 3.0,
    channel_window: int = 20,
    max_hold_days: int = 20,
    vol_window: int = 20,
    median_window: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    si = _swing_index(df, limit_move=limit_move)
    asi = si.cumsum()

    prior_high = asi.shift(1).rolling(channel_window, min_periods=channel_window).max()
    prior_low = asi.shift(1).rolling(channel_window, min_periods=channel_window).min()

    low_vol = _low_vol_regime(close, vol_window, median_window)

    entry = (asi > prior_high) & low_vol
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
            # exit stays active regardless of regime (only entry is gated)
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
