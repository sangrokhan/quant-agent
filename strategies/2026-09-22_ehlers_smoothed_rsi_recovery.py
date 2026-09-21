"""Strategy: Ehlers Smoothed RSI (SRSI) oversold-recovery crossover, trend
gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-016):
Per ProRealCode's implementation of John Ehlers' "RSI Smoothing" paper
(https://www.prorealcode.com/prorealtime-indicators/john-ehlers-smoothed-rsi/,
visited this iteration; original source
http://www.stockspotter.com/Files/rsismoothing.pdf): price is first passed
through a 4-tap FIR low-pass filter
    Smooth[t] = (C[t] + 2*C[t-1] + 2*C[t-2] + C[t-3]) / 6
(a binomial-weighted moving average that removes 2-3 bar noise before RSI is
computed), and Wilder's classic up-move/down-move summation RSI is then
computed on this SMOOTHED price series instead of raw close, producing a
much less jittery oscillator than plain RSI at the same lookback length.

The source itself only shows an indicator comparison chart (Ehlers'
Smoothed RSI vs. Wilder's raw RSI) with no disclosed trading rule, so this
strategy applies this repo's standard convention for such cases: a
30/70-style oversold-recovery long entry (SRSI crosses back above
oversold_level having recently been below it) gated by a long-term SMA
uptrend filter, exiting on SRSI reaching overbought_level, falling back
below oversold_level, or a max_hold_days time-stop. This 4-tap FIR
smoothing kernel is distinct from every other smoothed-RSI variant already
in this repo (Hann-window RSI 2026-09-12-148 uses a cosine-taper FIR of a
different order/shape; OC-sampled RSI 2026-09-17-167 uses (Open+Close)/2 as
input with NO extra FIR smoothing; Cutler's RSI uses an SMA instead of
Wilder's EMA for the gain/loss averaging step, not price smoothing at all).

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


def _ehlers_smoothed_rsi(close: pd.Series, window: int) -> pd.Series:
    smooth = (close + 2 * close.shift(1) + 2 * close.shift(2) + close.shift(3)) / 6.0

    delta = smooth.diff()
    up_move = delta.clip(lower=0.0)
    down_move = -delta.clip(upper=0.0)

    cu = up_move.rolling(window).sum()
    cd = down_move.rolling(window).sum()

    total = (cu + cd).replace(0.0, float("nan"))
    srsi = (cu / total) * 100.0
    return srsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    trend_window: int = 200,
    oversold_level: float = 30.0,
    overbought_level: float = 70.0,
    lookback_days: int = 5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    srsi = _ehlers_smoothed_rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    was_oversold = srsi.rolling(lookback_days, min_periods=1).min().le(oversold_level)
    cross_up = (srsi > oversold_level) & (srsi.shift(1) <= oversold_level)
    entry = cross_up & was_oversold.shift(1).fillna(False) & uptrend.fillna(False)

    exit_overbought = srsi >= overbought_level
    exit_oversold_again = srsi < oversold_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or bool(exit_oversold_again.iloc[i]) or held >= max_hold_days:
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
