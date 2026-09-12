"""Strategy: Ehlers Ultimate Oscillator (dual-highpass, RMS-normalized) zero-cross.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per John Ehlers' TASC April 2025 article (transcribed with full C code at
https://financial-hacker.com/ehlers-ultimate-oscillator/, Petra Volkova):
the Ultimate Oscillator is built from the DIFFERENCE of two 2-pole highpass
filters at different periods (`Edge` for the fast/short cutoff, `Width *
Edge` for the slow/long cutoff), normalized by a 100-bar root-mean-square
to convert the output to roughly standard-deviation units. The source
demonstrates the oscillator visually tracks market direction with near-
zero lag on an SPX chart but discloses no explicit trading rule beyond
"follow the chart" -- this strategy tests the natural zero-crossing signal
implied by the construction: long when the oscillator crosses from
negative to positive (direction turning up), exit on the reverse cross.

This is architecturally distinct from two already-tested Ehlers dual-
highpass strategies in this repo: the Cybernetic Oscillator (2026-09-07-
002, trades when BOTH raw highpass series' 2-bar ROC are simultaneously
positive, no RMS normalization or oscillator difference) and Precision
Trend Analysis (2026-09-12-171, uses 3-pole highpass and trades on the
turning points of the difference's own rate-of-change, not a zero-cross of
the normalized difference itself).

Signal logic
------------
- HighPass3(price, period): standard Ehlers 2-pole highpass filter.
- Signal = HighPass3(price, width*edge) - HighPass3(price, edge)
  (difference of a slow and fast highpass -- the "band-limited" component).
- UltOsc = Signal / RMS(Signal, rms_window) (100-bar RMS, per source).
- Long entry: UltOsc crosses from <=0 to >0.
- Exit: UltOsc crosses back to <=0, or a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _highpass3(price: np.ndarray, period: int) -> np.ndarray:
    """2-pole highpass filter (Ehlers standard coefficients, 'HighPass3')."""
    n = len(price)
    out = np.zeros(n)
    a1 = np.exp(-1.414 * np.pi / period)
    c2 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0
    for i in range(2, n):
        out[i] = (
            c1 * (price[i] - 2 * price[i - 1] + price[i - 2])
            + c2 * out[i - 1]
            + c3 * out[i - 2]
        )
    return out


def generate_signals(
    price_df: pd.DataFrame,
    edge: int = 20,
    width: int = 2,
    rms_window: int = 100,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    price = close.to_numpy(dtype=float)

    hp_slow = _highpass3(price, width * edge)
    hp_fast = _highpass3(price, edge)
    signal = hp_slow - hp_fast

    signal_sq = pd.Series(signal ** 2, index=close.index)
    rms = np.sqrt(signal_sq.rolling(rms_window).mean())
    ult_osc = pd.Series(signal, index=close.index) / rms.replace(0.0, np.nan)

    above = ult_osc > 0
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
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
