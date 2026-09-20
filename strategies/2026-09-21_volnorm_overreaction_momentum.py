"""Strategy: Volatility-normalized "overreaction" momentum continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-206):
Source: https://arxiv.org/html/2602.18912v1 ("Overreaction as an indicator
for momentum in algorithmic trading: A Case of AAPL stocks", Lis/Slepaczuk/
Sakowski, Feb 2026). The paper defines "overreaction" as an extreme return
realization relative to contemporaneous (rolling) volatility, models it as a
predictor of short-term momentum continuation, and finds (as a non-ML
baseline, distinct from their ML/sentiment-feature models which need Twitter
data unavailable to this repo) that "classical behavioral momentum effects
dominate at intermediate frequencies". This strategy operationalizes that as
a purely price-based (OHLCV-only) daily-bar rule: flag days where the
day's return, normalized by trailing realized volatility, exceeds a
threshold ("overreaction"), then go long expecting short-term continuation.
Distinct from existing RSI(2)/day-of-week entries already in this KB (id
2026-09-03-005, 2026-09-20-002) -- this is a volatility-normalized magnitude
threshold on raw daily return, not an oscillator or calendar effect.

Signal logic
------------
- daily_ret = pct change of close.
- rolling_vol = trailing std of daily_ret over `vol_window` days.
- overreaction_z = daily_ret / rolling_vol (z-score-like normalized shock).
- Entry (long): overreaction_z >= `entry_z` (a large positive one-day move
  relative to recent volatility) -- bet on momentum continuation the
  following day(s).
- Exit: hold for a fixed `hold_days` short horizon (the paper's finding is
  that continuation is strongest at "intermediate" -- i.e. short --
  frequencies, so this uses a fixed short time-stop rather than an
  indicator-based exit) OR overreaction_z drops back below `exit_z`
  (momentum has faded).
- Flat otherwise.

Interface contract (validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    vol_window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    rolling_vol = daily_ret.rolling(vol_window).std()
    overreaction_z = daily_ret / rolling_vol.replace(0, pd.NA)

    entry = overreaction_z >= entry_z
    exit_fade = overreaction_z < exit_z

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            fade = bool(exit_fade.iloc[i]) if not pd.isna(exit_fade.iloc[i]) else False
            if fade or held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            trig = bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False
            if trig:
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
