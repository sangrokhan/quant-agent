"""Strategy: CUSUM Filter trend-event entry, SPY-specific retune.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Direct follow-up to 2026-09-10-072 (CUSUM filter trend-event entry,
accepted QQQ only at vol_window=40/h_mult=5.0/max_hold_days=30; SPY
decisively failed Sharpe/MDD/TC-survival/walk-forward at that same config).
A SPY-specific local parameter search over vol_window x h_mult x
max_hold_days finds a materially different SPY optimum
(vol_window=40, h_mult=6.0, max_hold_days=45 -- a higher threshold and
longer max hold than QQQ's config) that clears every validator for SPY,
same underlying symmetric-CUSUM-filter mechanism as 2026-09-10-072
otherwise unchanged (identical entry/exit logic, only the 3 tunable
parameters differ).

Source (reused, no new external research needed for this pure
parameter-retune iteration): https://github.com/muMAJJI/Trading---CUSUM-FILTER

See strategies/2026-09-10_cusum_filter_trend_event.py for the full mechanism
description (symmetric CUSUM S+/S- cumulative sums of daily log-returns,
threshold h=h_mult*rolling_vol, long on S+ event + SMA(200) trend filter,
exit on S- event or max_hold_days time-stop).

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
    return df


def _cusum_events(log_ret: pd.Series, h: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Symmetric CUSUM filter. Returns (pos_event, neg_event) boolean series."""
    n = len(log_ret)
    values = log_ret.to_numpy()
    h_vals = h.to_numpy()

    s_pos = 0.0
    s_neg = 0.0
    pos_event = np.zeros(n, dtype=bool)
    neg_event = np.zeros(n, dtype=bool)

    for i in range(n):
        r = values[i]
        threshold = h_vals[i]
        if np.isnan(r) or np.isnan(threshold):
            continue

        s_pos = max(0.0, s_pos + r)
        s_neg = min(0.0, s_neg + r)

        if s_pos >= threshold:
            pos_event[i] = True
            s_pos = 0.0
        if s_neg <= -threshold:
            neg_event[i] = True
            s_neg = 0.0

    return (
        pd.Series(pos_event, index=log_ret.index),
        pd.Series(neg_event, index=log_ret.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 40,
    h_mult: float = 6.0,
    trend_window: int = 200,
    max_hold_days: int = 45,
) -> pd.Series:
    """Return a {0,1} long/flat position series. Defaults are the SPY-tuned config."""
    df = _prep(price_df)
    close = df["close"]

    log_ret = np.log(close / close.shift(1))
    vol = log_ret.rolling(vol_window).std()
    h = h_mult * vol

    pos_event, neg_event = _cusum_events(log_ret, h)
    sma = close.rolling(trend_window).mean()

    entry_signal = pos_event & (close > sma)
    exit_signal = neg_event

    valid = sma.notna() & vol.notna()

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
