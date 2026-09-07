"""Strategy: Ehlers Fisher Stochastic Relative Vigor Index (RVI) crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-029):
Per John Ehlers' "Cybernetic Analysis for Stocks and Futures" (pgs 101-104,
as summarized by FMZ's strategy writeup at
https://www.fmz.com/lang/en/strategy/436218 and TradingView's "Ehlers Fisher
Stochastic Relative Vigor Index [CC]" indicator page
https://www.tradingview.com/script/vGWGjnc4-Ehlers-Fisher-Stochastic-Relative-Vigor-Index-CC/):
Ehlers' original Relative Vigor Index (RVI, close-vs-open normalized by
high-low range) is first turned into a STOCHASTIC (rescaled to the
-1..+1 range using its own rolling high/low over a lookback window, per
the generic Ehlers stochastic-normalization pattern confirmed via the
Fisher-of-stochastic Pine snippet found in Google's SERP -- "value1 =
2*(src-lowestLow)/(highestHigh-lowestLow)-1"), then a FISHER TRANSFORM is
applied to that stochastic-normalized RVI to sharpen turning points and
produce a signal/trigger crossover system. This is a genuinely new
two-stage construction in this repo: distinct from the existing plain RVI
crossover strategies (2026-09-04-061/130/147, which cross raw
SMA-smoothed RVI against its own SMA signal line) and distinct from the
existing Fisher-Transform-of-price strategies (2026-09-04-051,
2026-09-05-086, which apply the Fisher transform directly to price/high-low
midpoint) -- here the Fisher transform is applied to a STOCHASTIC-NORMALIZED
RVI, a categorically different input series (bounded oscillator-of-an-
oscillator, not raw price).

Signal logic
------------
1. RVI = SMA((Close-Open)/(High-Low), rvi_length)  -- standard RVI numerator
   normalized per-bar by trading range, then smoothed (matches 2026-09-04-147
   base definition, reused as the well-established RVI construction).
2. Stochastic-normalize RVI over stoch_length: rescale RVI's position within
   its own rolling [min, max] window to -1..+1 (clamped away from the
   endpoints to keep the Fisher transform's log well-defined).
3. Smooth the -1..+1 series with an EMA (fisher_smooth) to reduce noise
   before the Fisher transform (per the generic Ehlers Fisher-of-stochastic
   pattern).
4. Fisher = 0.5*ln((1+v)/(1-v)); Trigger = Fisher shifted by 1 bar (Ehlers'
   own standard "compare Fisher to its prior value" trigger line).
5. Long entry: Fisher crosses above Trigger. Exit: Fisher crosses below
   Trigger, or a max_hold_days time-stop (added for robustness, not in the
   original -- the source's own fixed/trailing-stop risk control is
   approximated here with a simple time-stop given this repo's vectorbt-based
   validator suite doesn't take intrabar stop levels).
6. Flat otherwise; long-only, matching repo convention.

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


def _fisher_stochastic_rvi(
    df: pd.DataFrame, rvi_length: int, stoch_length: int, fisher_smooth: int
) -> pd.Series:
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    rng = (high - low).replace(0, np.nan)
    v_t = (close - open_) / rng
    rvi = v_t.rolling(rvi_length).mean()

    lowest = rvi.rolling(stoch_length).min()
    highest = rvi.rolling(stoch_length).max()
    span = (highest - lowest).replace(0, np.nan)
    stoch = 2.0 * (rvi - lowest) / span - 1.0
    stoch = stoch.clip(-0.999, 0.999)

    smoothed = stoch.ewm(span=fisher_smooth, min_periods=fisher_smooth, adjust=False).mean()
    smoothed = smoothed.clip(-0.999, 0.999)

    fisher = 0.5 * np.log((1.0 + smoothed) / (1.0 - smoothed))
    return fisher


def generate_signals(
    price_df: pd.DataFrame,
    rvi_length: int = 10,
    stoch_length: int = 20,
    fisher_smooth: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    fisher = _fisher_stochastic_rvi(df, rvi_length, stoch_length, fisher_smooth)
    trigger = fisher.shift(1)

    cross_up = (fisher > trigger) & (fisher.shift(1) <= trigger.shift(1))
    cross_down = (fisher < trigger) & (fisher.shift(1) >= trigger.shift(1))

    valid = fisher.notna() & trigger.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
