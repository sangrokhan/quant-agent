"""Strategy: Chande Momentum Oscillator (CMO) mean-reversion snapback with a
time-based stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-029):
Source: Google AI Overview synthesis (search "Chande Momentum Oscillator CMO
trading strategy specific threshold rule backtest"), read via browser_exec
Google SERP fallback (web_search DDGS backend errored this iteration). The
disclosed rule set:
  - CMO(9) (a 9-period Chande Momentum Oscillator, standard formula:
    100 * (sum of up moves - sum of down moves) / (sum of up moves + sum of
    down moves) over the lookback window).
  - Long entry: CMO drops below -50 (oversold) then crosses back above -50
    (mean-reverting snapback), i.e. buy the oversold bounce.
  - Exit: CMO rises above +50 (overbought) or crosses back below +50 after
    having been above it, OR a forced time-based stop after 5 trading bars
    (prevents holding through extended trend exhaustion where CMO can stay
    pinned near an extreme during strong trends -- the source explicitly
    flags choppy/strong-trend markets as the failure mode).
No indicator family named "CMO"/"Chande Momentum" or technique
"mean_reversion_snapback"/"time_stop" appears anywhere in this repo's prior
knowledge_base entries (checked via strategies_index.jsonl grep before
writing this file) -- this is a genuinely novel indicator family for this
KB, distinct from the Stochastic/RSI/Williams %R oscillator-threshold
strategies already tried (CMO's normalization -- net directional move over
total move, not average gain/loss like RSI -- gives it different dynamics,
particularly in choppy markets).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cmo(close: pd.Series, window: int) -> pd.Series:
    """Chande Momentum Oscillator: 100 * (sum up - sum down) / (sum up + sum down)."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    sum_up = up.rolling(window).sum()
    sum_down = down.rolling(window).sum()
    denom = (sum_up + sum_down).replace(0.0, pd.NA)
    cmo = 100 * (sum_up - sum_down) / denom
    return cmo.astype(float).fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    cmo_window: int = 9,
    oversold_threshold: float = -50.0,
    overbought_threshold: float = 50.0,
    max_hold_bars: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    cmo = _cmo(close, cmo_window)

    was_oversold = cmo.shift(1) < oversold_threshold
    entry_signal = was_oversold & (cmo >= oversold_threshold)
    exit_signal = cmo >= overbought_threshold

    pos_vals = []
    in_pos = False
    bars_held = 0
    for i in range(len(close)):
        if in_pos:
            bars_held += 1
            if bool(exit_signal.iloc[i]) or bars_held >= max_hold_bars:
                in_pos = False
                bars_held = 0
        elif bool(entry_signal.iloc[i]):
            in_pos = True
            bars_held = 0
        pos_vals.append(1 if in_pos else 0)

    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    cmo_window: int = 9,
    oversold_threshold: float = -50.0,
    overbought_threshold: float = 50.0,
    max_hold_bars: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        cmo_window=cmo_window,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        max_hold_bars=max_hold_bars,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
