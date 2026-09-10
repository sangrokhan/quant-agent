"""Strategy: Balance of Power (BOP) bullish-divergence long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://trendspider.com/learning-center/balance-of-power-a-comprehensive-guide-for-traders/:
"Traders often look for convergence and divergence between the Balance of
Power indicator and the price chart to identify potential trend reversals.
... divergence happens when the price and the indicator move in opposite
directions. The divergence between the Balance of Power and price can be a
strong signal of an impending reversal." No precise numeric swing-detection
rule is given by the source (generic qualitative description only), so this
implementation operationalizes it using this repo's established
swing-low-divergence pattern (already proven testable in prior divergence
entries -- A/D Line divergence 2026-09-06-138, Elder-Ray Bull Power
divergence 2026-09-06-135, MFI divergence 2026-09-05-061): price makes a
LOWER swing low while BOP makes a HIGHER swing low at the same bar (selling
pressure weakening despite the new price low). First BOP DIVERGENCE variant
in this repo -- BOP itself (non-divergence, threshold-crossing) already has
3 prior entries, but no divergence construction has been tested.

Signal logic
------------
- BOP_t = (Close_t - Open_t) / (High_t - Low_t) (in [-1, 1]).
- Identify local swing lows in price (a close that is the minimum within a
  trailing +/- `swing_window` bar window).
- Bullish divergence: at a swing-low bar, price is LOWER than the prior
  price swing low, while BOP's value at the same bar is HIGHER than BOP's
  value at the prior price swing low.
- Entry (long): on the bar the bullish divergence is confirmed.
- Exit: close crosses back above its `exit_sma_window`-day SMA (mean
  reversion / trend re-confirmation, consistent with other divergence
  strategies in this repo), OR after `max_hold_days` (time-stop backstop).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _bop(df: pd.DataFrame) -> pd.Series:
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    rng = (high - low).replace(0.0, np.nan)
    bop = (close - open_) / rng
    return bop.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    exit_sma_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    bop = _bop(df)

    n = len(close)
    is_swing_low = pd.Series(False, index=close.index)
    close_vals = close.values
    for i in range(swing_window, n - swing_window):
        window = close_vals[i - swing_window : i + swing_window + 1]
        if close_vals[i] == window.min():
            is_swing_low.iloc[i] = True

    swing_low_idxs = list(np.where(is_swing_low.values)[0])

    entry = pd.Series(False, index=close.index)
    prev_swing_i = None
    for i in swing_low_idxs:
        if prev_swing_i is not None:
            price_lower_low = close_vals[i] < close_vals[prev_swing_i]
            bop_higher_low = bop.iloc[i] > bop.iloc[prev_swing_i]
            if price_lower_low and bop_higher_low:
                entry.iloc[i] = True
        prev_swing_i = i

    sma = close.rolling(exit_sma_window).mean()
    exit_meanrev = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
