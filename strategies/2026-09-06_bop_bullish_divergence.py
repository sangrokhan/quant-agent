"""Strategy: Balance of Power (BOP) bullish divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per this iteration's research (LuxAlgo's BOP guide), the Balance of Power
indicator BOP = (Close - Open) / (High - Low) oscillates between -1 and
+1, measuring where the close sits within the day's range as a proxy for
buyer/seller control. The source explicitly lists "divergences (price vs
BOP)" as a recognized BOP signal, distinct from the already-tested
zero-line-crossover variant (2026-09-04-071, rejected). This strategy
implements the divergence variant: a bullish divergence occurs when price
makes a new swing low while smoothed BOP makes a HIGHER low at the same
point (sellers are technically pushing price down but losing intraday
control, per the source's close-within-range interpretation) -- a
classic exhaustion signal. Long entry on BOP subsequently crossing back
above a confirmation level within a confirmation window; exit on reverse
cross, BOP reaching an overbought exit level, or a time-stop. First
BOP-divergence strategy in this repo -- distinct from the plain BOP
zero-line-crossover (2026-09-04-071) and RVI (2026-09-04-147, a
double-smoothed signal-line variant of the same close-vs-open concept).

Signal logic
------------
- raw_bop = (close - open) / (high - low), with (high-low)==0 handled as
  0 to avoid division errors.
- bop = SMA(raw_bop, smooth_window) (source's own smoothing recommendation).
- Swing low detection: a bar t is a local swing low if bop's underlying
  price (close) is the minimum over a trailing swing_lookback window.
- Bullish divergence: at a new swing low (close lower than the prior
  swing low), bop is HIGHER than bop was at the prior swing low.
- Entry (long): within confirm_window bars of a flagged divergence, bop
  crosses above confirm_level (source's readings: modest positive value,
  default 0.1, well below the naive 0.8 threshold which never triggers
  on smoothed daily bars per the already-tested crossover strategy's own
  finding).
- Exit: bop crosses back below confirm_level after being above it, bop
  reaches exit_level (overbought, default 0.5), or a max_hold_days
  time-stop.

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


def generate_signals(
    price_df: pd.DataFrame,
    smooth_window: int = 14,
    swing_lookback: int = 10,
    confirm_level: float = 0.1,
    exit_level: float = 0.5,
    confirm_window: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    range_ = (high - low).replace(0, np.nan)
    raw_bop = (close - open_) / range_
    raw_bop = raw_bop.fillna(0.0)
    bop = raw_bop.rolling(smooth_window).mean()

    is_swing_low = close == close.rolling(swing_lookback * 2 + 1, center=True).min()

    n = len(close)
    divergence = pd.Series(False, index=close.index)
    last_swing_low_idx = None
    last_swing_low_price = None
    last_swing_low_bop = None

    for i in range(n):
        if bool(is_swing_low.iloc[i]) if not pd.isna(is_swing_low.iloc[i]) else False:
            cur_price = close.iloc[i]
            cur_bop = bop.iloc[i]
            if (
                last_swing_low_idx is not None
                and not pd.isna(cur_bop)
                and not pd.isna(last_swing_low_bop)
                and cur_price < last_swing_low_price
                and cur_bop > last_swing_low_bop
            ):
                divergence.iloc[i] = True
            last_swing_low_idx = i
            last_swing_low_price = cur_price
            last_swing_low_bop = cur_bop

    bop_above = bop > confirm_level
    confirm_cross = bop_above & (~bop_above.shift(1).fillna(False))

    entry = pd.Series(False, index=close.index)
    pending_divergence_idx = None
    for i in range(n):
        if bool(divergence.iloc[i]):
            pending_divergence_idx = i
        if pending_divergence_idx is not None and i - pending_divergence_idx <= confirm_window:
            if bool(confirm_cross.iloc[i]) and i > pending_divergence_idx:
                entry.iloc[i] = True
                pending_divergence_idx = None
        elif pending_divergence_idx is not None and i - pending_divergence_idx > confirm_window:
            pending_divergence_idx = None

    exit_reverse = bop < confirm_level
    exit_overbought = bop >= exit_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_reverse.iloc[i]) or bool(exit_overbought.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    smooth_window: int = 14,
    swing_lookback: int = 10,
    confirm_level: float = 0.1,
    exit_level: float = 0.5,
    confirm_window: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: position (lagged by 1 bar to avoid
    lookahead) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        smooth_window=smooth_window,
        swing_lookback=swing_lookback,
        confirm_level=confirm_level,
        exit_level=exit_level,
        confirm_window=confirm_window,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
