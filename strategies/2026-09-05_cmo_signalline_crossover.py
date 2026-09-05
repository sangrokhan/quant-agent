"""Strategy: Chande Momentum Oscillator (CMO) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-064):
Per https://www.quantifiedstrategies.com/chande-momentum-oscillator-trading-strategy/ :
"Some traders also add a 9-period moving average of the CMO to the
indicator as a signal line. When the indicator crosses above the signal
line, they consider it a bullish signal, and when it drops below the
signal line, they consider it a bearish signal." The same source's own
backtest found a short (5-day) max holding period outperformed longer
holds (10/15/30 days saw returns decrease as hold lengthened).

This is a DISTINCT mechanism from the already-rejected
2026-09-04-055 CMO oversold-reversal strategy: that one used a fixed
-50/+50 threshold-cross-back-up rule plus a 200-day SMA trend filter.
Here the entry/exit trigger is purely the CMO crossing its own N-period
moving-average signal line (a relative/adaptive threshold, not a fixed
absolute level), with NO separate trend filter -- testing the source's
own stated alternative rule set on its own terms.

CMO formula (standard, Chande):
    diff = close.diff()
    up_sum = diff.clip(lower=0).rolling(window).sum()
    down_sum = (-diff.clip(upper=0)).rolling(window).sum()
    CMO = 100 * (up_sum - down_sum) / (up_sum + down_sum)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
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


def _cmo(close: pd.Series, window: int = 9) -> pd.Series:
    diff = close.diff()
    up_sum = diff.clip(lower=0).rolling(window).sum()
    down_sum = (-diff.clip(upper=0)).rolling(window).sum()
    total = up_sum + down_sum
    cmo = 100.0 * (up_sum - down_sum) / total.replace(0, pd.NA)
    return cmo.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    cmo_window: int = 9,
    signal_window: int = 9,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: CMO crosses above its own `signal_window`-period SMA.
    Exit: CMO crosses back below the signal line, OR a max_hold_days
    time-stop (per the source's own finding that shorter holds outperform).
    """
    df = _prep(price_df)
    close = df["close"]

    cmo = _cmo(close, window=cmo_window)
    signal_line = cmo.rolling(signal_window).mean()

    prev_cmo = cmo.shift(1)
    prev_signal = signal_line.shift(1)

    bullish_cross = (prev_cmo <= prev_signal) & (cmo > signal_line)
    bearish_cross = (prev_cmo >= prev_signal) & (cmo < signal_line)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if bool(bearish_cross.iloc[i]) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
                in_position = True
                hold_days = 0
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
