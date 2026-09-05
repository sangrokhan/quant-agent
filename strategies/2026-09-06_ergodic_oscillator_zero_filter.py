"""Strategy: William Blau's Ergodic Oscillator, signal-line crossover gated
by a zero-line trend regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-102):
Per LuxAlgo's Ergodic Oscillator library page: the Ergodic Oscillator is
William Blau's double-smoothed momentum ratio (one-bar price change passed
through a long-length then short-length EMA, divided by the identical
pipeline applied to the absolute change, scaled to +/-100), with a
signal-line (EMA of the ergodic line). The source's own trading guidance:
"Signal-line crosses: the momentum triggers -- best taken with the zero
line or a trend filter as referee" and "Zero crosses: net double-smoothed
momentum changing sign, the slower trend-change cue." This combines both:
long entry on a signal-line cross-up while the ergodic line is already
above zero (using the zero line as the "referee" trend filter the source
recommends). Distinct from this repo's already-tested Blau-family
indicators: True Strength Index (2026-09-04-129, zero-line-filtered
signal-line cross, REJECTED) and Stochastic Momentum Index (2026-09-04-140,
oversold-threshold signal-line cross, REJECTED) -- the Ergodic Oscillator
itself (Blau's original, simpler double-EMA-smoothed-momentum-ratio
construction, not TSI's EMA-of-EMA-of-momentum-then-ratio variant or SMI's
stochastic-position construction) has never been tested under this name in
this repo.

Source: https://www.luxalgo.com/library/indicator/ergodic-oscillator/

Signal logic
------------
- Ergodic = 100 * EMA(EMA(price.diff(1), long_len), short_len) /
            EMA(EMA(price.diff(1).abs(), long_len), short_len)
- Signal = EMA(Ergodic, signal_len)
- Entry (long): Ergodic crosses above Signal AND Ergodic > 0 at the cross
  (zero-line trend filter).
- Exit: Ergodic crosses below Signal, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ergodic(close: pd.Series, long_len: int, short_len: int, signal_len: int) -> tuple[pd.Series, pd.Series]:
    diff = close.diff(1)
    num = diff.ewm(span=long_len, adjust=False).mean().ewm(span=short_len, adjust=False).mean()
    den = diff.abs().ewm(span=long_len, adjust=False).mean().ewm(span=short_len, adjust=False).mean()
    ergodic = 100 * (num / den)
    signal = ergodic.ewm(span=signal_len, adjust=False).mean()
    return ergodic, signal


def generate_signals(
    price_df: pd.DataFrame,
    long_len: int = 20,
    short_len: int = 5,
    signal_len: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ergodic, signal = _ergodic(close, long_len, short_len, signal_len)

    cross_up = (ergodic > signal) & (ergodic.shift(1) <= signal.shift(1))
    cross_down = (ergodic < signal) & (ergodic.shift(1) >= signal.shift(1))

    entry = (cross_up & (ergodic > 0)).fillna(False)
    exit_signal = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
