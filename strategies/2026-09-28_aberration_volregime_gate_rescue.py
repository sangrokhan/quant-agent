"""Strategy: Aberration (Keith Fitschen, 1986) trend-following breakout with
monotonic trailing-stop exit, long-only, PLUS a low-volatility-regime gate.

Rescue attempt for near-miss id 2026-09-06-144 (Aberration ratcheted-stop
breakout, rejected: Sharpe 0.927 narrowly missed 1.0, MDD 0.2565 narrowly
exceeded 0.25, parameter sensitivity 0.603 decisively failed at 0.5
threshold). That entry's own `notes` explicitly flagged the fix: "a future
loop could revisit with an explicit low-vol regime gate given the stark
vol-regime split (low pass_fraction 0.407 vs mid 0.130 vs high 0.0)" -- i.e.
the grid showed the edge is real and concentrated almost entirely in the
low-volatility tercile, and flattening out of trades during mid/high-vol
regimes (rather than accepting the strategy's naive always-in-the-market
posture) should fix both the Sharpe near-miss (avoiding the choppy
high-vol losing trades that drag down the blended full-sample Sharpe) and
the MDD near-miss (avoiding the deep high-vol drawdowns) simultaneously,
per this repo's established "regime filter fixes a low-vol-concentrated
near-miss" pattern (e.g. strategies/2026-09-03_bb_meanrev_qqq_volregime.py).

Same core Aberration signal logic (unmodified) plus one new parameter:
`vol_regime_ratio` -- entries are only taken when a fast realized-vol
proxy (rolling std of daily returns over `vol_fast_window`) is at or below
`vol_regime_ratio` times its own slower rolling average (`vol_slow_window`),
i.e. "current volatility is calm relative to its own recent history" --
this is a self-referential low-vol gate (does not require external
vol_regime_splits labeling at strategy-code time, works standalone).
Existing open positions are NOT force-closed by a mid-trade vol spike (the
existing ratcheted-stop/time-stop exits already handle that) -- the gate
only suppresses NEW entries during elevated-volatility regimes.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    std_mult: float = 2.0,
    max_hold_days: int = 60,
    vol_fast_window: int = 20,
    vol_slow_window: int = 100,
    vol_regime_ratio: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma = close.rolling(sma_window).mean()
    std = close.rolling(sma_window).std()
    upper_band = sma + std_mult * std

    daily_ret = close.pct_change()
    vol_fast = daily_ret.rolling(vol_fast_window).std()
    vol_slow = vol_fast.rolling(vol_slow_window).mean()
    low_vol_regime = (vol_fast <= vol_regime_ratio * vol_slow).fillna(False)

    breakout = (close > upper_band) & low_vol_regime

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    ratchet_stop = np.nan
    for i in range(n):
        if in_position:
            held = i - entry_idx
            cur_sma = sma.iloc[i]
            if not np.isnan(cur_sma):
                ratchet_stop = cur_sma if np.isnan(ratchet_stop) else max(ratchet_stop, cur_sma)
            stop_break = (not np.isnan(ratchet_stop)) and (close.iloc[i] < ratchet_stop)
            if stop_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                ratchet_stop = np.nan
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(breakout.iloc[i]):
                in_position = True
                entry_idx = i
                ratchet_stop = sma.iloc[i]
                position.iloc[i] = leverage_cap
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
