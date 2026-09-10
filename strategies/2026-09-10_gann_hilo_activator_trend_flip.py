"""Strategy: Gann HiLo Activator trend-flip (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per https://trendsandbreakouts.com/gann-hilo-activator (Gann HiLo Activator,
attributed to W.D. Gann's high/low-average trailing trend concept): a
state-machine trend line built from two simple moving averages of High and
Low over a short lookback window (source default n=3, also commonly 5/8/10)
flips its plotted line between the highs-average (downtrend, resistance
above price) and the lows-average (uptrend, support below price). Source's
disclosed rule set: if Close > prior HMA(n), state -> uptrend; if Close <
prior LMA(n), state -> downtrend; otherwise keep the prior state. This
implementation trades the state FLIP itself: go long the bar after the
state flips from downtrend to uptrend (a "stop-and-reverse" trailing-line
cross similar in spirit to Supertrend/Parabolic SAR, but built from
High/Low SMAs rather than ATR bands or parabolic acceleration), exit when
the state flips back to downtrend or after a max_hold_days time-stop.
First Gann HiLo Activator strategy in this repo -- distinct from ATR-based
Supertrend/Chandelier-exit trailing-stop strategies and from all prior
"Gann" family entries (Gann angles/fan lines) since this is a pure
High/Low-SMA state-machine trend line, no ATR or geometric-angle math.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Both accept keyword-arg tunable parameters per RESEARCH_LOOP.md Step 5.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gann_hilo_state(df: pd.DataFrame, n: int) -> pd.Series:
    """Return the Gann HiLo Activator trend state series: 1 = uptrend, -1 = downtrend.

    State machine per source's disclosed rule:
      if Close > prior HMA(n): state = uptrend
      if Close < prior LMA(n): state = downtrend
      else: keep prior state
    """
    close = df["close"]
    hma = df["high"].rolling(n).mean()
    lma = df["low"].rolling(n).mean()
    prior_hma = hma.shift(1)
    prior_lma = lma.shift(1)

    state = pd.Series(index=close.index, dtype=float)
    prev_state = 1  # arbitrary initial state before enough data
    for i in range(len(close)):
        c = close.iloc[i]
        ph = prior_hma.iloc[i]
        pl = prior_lma.iloc[i]
        if pd.isna(ph) or pd.isna(pl):
            state.iloc[i] = float("nan")
            continue
        if c > ph:
            prev_state = 1
        elif c < pl:
            prev_state = -1
        # else keep prev_state unchanged
        state.iloc[i] = prev_state
    return state


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 3,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long while the Gann HiLo state is in "uptrend" (1); flat while in
    "downtrend" (-1). Position enters the bar AFTER the flip is confirmed
    (using the already-lagged prior_hma/prior_lma comparison baked into
    _gann_hilo_state, plus a further shift(1) in generate_returns to avoid
    look-ahead bias on the trade itself).
    """
    df = _prep(price_df)
    close = df["close"]

    state = _gann_hilo_state(df, n=n)
    long_flag = (state == 1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if not bool(long_flag.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_flag.iloc[i]):
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
