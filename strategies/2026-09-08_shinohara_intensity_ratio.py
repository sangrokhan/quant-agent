"""Strategy: Shinohara Intensity Ratio (SIR), smoothed Strong/Weak Ratio
crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-051):
Per theforexgeek.com's Shinohara Intensity Ratio explainer (browser_exec
fallback -- web_search's DuckDuckGo backend errored on the first query with
a TLS connection error), the raw per-bar formulas are:
    Strong Ratio = (Close - Low) / (High - Low)
    Weak Ratio   = (High - Close) / (High - Low)
Note: for a single bar these two always sum to 1.0 (a purely mechanical
identity, not a market signal), so using the *raw* per-bar values directly
would produce a trivially anti-correlated, non-informative crossover. This
repo's adaptation smooths each ratio with a rolling SMA over `sir_window`
periods before comparing them -- consistent with gocharting.com's own
framing of the strategy in terms of one ratio being "significantly higher"
than the other over a sustained period, not a single-bar snapshot (also
corroborated by gocharting's own "do not use as a standalone timing
indicator... ratio can stay elevated during sustained trends" caution).

Source's own explicit buy/sell rule (theforexgeek.com): buy when Strong
Ratio crosses above Weak Ratio (uptrend begins); sell/exit when Weak Ratio
crosses above Strong Ratio (downtrend begins) or the ratio spikes to an
extreme level and then turns down (momentum exhaustion). First Shinohara
Intensity Ratio strategy in this repo (0 prior hits).

Signal logic
------------
- StrongRatio_raw = (close - low) / (high - low)
- WeakRatio_raw = (high - close) / (high - low)
- StrongRatio = SMA(StrongRatio_raw, sir_window)
- WeakRatio = SMA(WeakRatio_raw, sir_window)
- Entry (long): StrongRatio crosses above WeakRatio.
- Exit: WeakRatio crosses above StrongRatio, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    sir_window: int = 14,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    rng = (high - low).replace(0, float("nan"))
    strong_raw = (close - low) / rng
    weak_raw = (high - close) / rng

    strong = strong_raw.rolling(sir_window).mean()
    weak = weak_raw.rolling(sir_window).mean()

    cross_up = (strong > weak) & (strong.shift(1) <= weak.shift(1))
    cross_down = (weak > strong) & (weak.shift(1) <= strong.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            cu = cross_up.iloc[i]
            if bool(cu) if pd.notna(cu) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            cd = cross_down.iloc[i]
            cd_bool = bool(cd) if pd.notna(cd) else False
            if cd_bool or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    sir_window: int = 14,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, sir_window=sir_window, max_hold_days=max_hold_days)
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
