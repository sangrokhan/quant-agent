"""Strategy: Elder Ray Bull/Bear Power contraction-recovery, confirmed by a
price-action swing-high breakout (rather than a bare indicator zero/slope
cross).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Bing's synthesized summary (trendsandbreakouts.com / chartingpath.com /
protraderdashboard.com) of Alexander Elder's Bull/Bear Power rules:
  1. Trend confirmation: 13-period EMA must be rising and price above it.
  2. Contraction/recovery: Bear Power (Low - EMA) is negative but has been
     rising over the recent window (bears losing conviction) -- a
     "contraction and recovery" phase.
  3. Entry trigger: the source explicitly states "Confirm with a price
     action signal, such as a break above a recent swing high for longs"
     -- i.e. the indicator condition alone is NOT the entry; a breakout
     above a recent N-day swing high is required.

This is distinct from every other Elder-Ray variant already tested in this
repo (2026-09-04-110 EMA-slope+BearPower-only trigger; 2026-09-06-135 /
2026-09-06-176 bullish-divergence variants; 2026-09-08-008 EMA-slope trend
filter) because none of them require an explicit swing-high price-action
breakout as the entry trigger -- they all fire directly off Bull/Bear Power
crossing/sloping, which is exactly the "false signal" mode this source's
own rule is designed to filter out.

Signal logic
------------
- trend_ema: EMA(ema_window) of close; require EMA rising (today > N bars
  ago) AND close > EMA (uptrend confirmation).
- Bear Power = Low - EMA. Contraction/recovery: Bear Power < 0 (still
  bearish pressure exists) AND Bear Power has risen over the trailing
  bp_lookback bars (min today's BP > BP bp_lookback bars ago).
- Entry trigger: close breaks above the highest close of the prior
  swing_window bars (a fresh swing-high breakout) while both of the above
  conditions hold simultaneously.
- Exit: EMA turns down (5-bar EMA slope negative), OR close breaks back
  below the lowest low of the prior swing_window bars (structural stop),
  OR max_hold_days time-stop.

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
    ema_window: int = 13,
    ema_slope_lookback: int = 5,
    bp_lookback: int = 5,
    swing_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    ema_rising = ema > ema.shift(ema_slope_lookback)
    uptrend = ema_rising & (close > ema)

    bear_power = low - ema
    bp_recovering = bear_power > bear_power.shift(bp_lookback)
    contraction_recovery = (bear_power < 0) & bp_recovering

    swing_high = close.shift(1).rolling(swing_window).max()
    swing_low = low.shift(1).rolling(swing_window).min()
    breakout_trigger = close > swing_high

    entry_signal = uptrend & contraction_recovery & breakout_trigger

    ema_turning_down = ema < ema.shift(ema_slope_lookback)
    structural_stop = close < swing_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = -1
    idx_list = close.index

    entry_arr = entry_signal.to_numpy()
    exit_arr = (ema_turning_down | structural_stop).to_numpy()

    pos_arr = [0] * len(idx_list)
    for i in range(len(idx_list)):
        if not in_position:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                pos_arr[i] = 1
        else:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_position = False
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1

    position = pd.Series(pos_arr, index=idx_list, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    ema_slope_lookback: int = 5,
    bp_lookback: int = 5,
    swing_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ema_window=ema_window,
        ema_slope_lookback=ema_slope_lookback,
        bp_lookback=bp_lookback,
        swing_window=swing_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Position at t applies to the return realized from t-1 close to t close
    # (i.e. shift position by 1 to avoid lookahead: signal decided on bar t's
    # close, position held starting next bar).
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
