"""Strategy: Trend Intensity Index (TII, M.H. Pee, 2002) midline cross.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-123):
The Trend Intensity Index (TII), developed by M.H. Pee (Stocks &
Commodities, June 2002), measures how one-sidedly price has deviated from
its own moving average. Source (stonehillforex.com) gives the exact
formula: compute a "major" SMA (default 60), then over the trailing
"minor" window (default 30 bars) sum the positive deviations (close >
major SMA) as SDPOS and the negative deviations (close < major SMA) as
SDNEG; TII = 100 * SDPOS / (SDPOS + SDNEG), range 0-100. The source
explicitly reframes this from a classic overbought/oversold oscillator
into a midline-cross confirmation indicator: TII crossing above 50 is a
bullish confirmation signal, crossing below 50 is bearish. We implement
long-only: enter when TII crosses above the midline (50), exit when TII
crosses back below the midline, or a max_hold_days time-stop.

Formula
-------
major_sma[i] = SMA(major_period) of close, ending at i
deviation[j] = close[j] - major_sma[j]  for j in the trailing minor_period window
SDPOS = sum(deviation[j] for j where deviation[j] > 0)
SDNEG = sum(-deviation[j] for j where deviation[j] < 0)
TII[i] = 100 * SDPOS / (SDPOS + SDNEG)

Signal logic
------------
- Entry (long): TII crosses from <=50 to >50.
- Exit: TII crosses from >50 to <=50, OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tii(close: pd.Series, major_period: int, minor_period: int) -> pd.Series:
    major_sma = close.rolling(major_period, min_periods=major_period).mean()
    deviation = close - major_sma

    pos_dev = deviation.clip(lower=0)
    neg_dev = (-deviation).clip(lower=0)

    sdpos = pos_dev.rolling(minor_period, min_periods=minor_period).sum()
    sdneg = neg_dev.rolling(minor_period, min_periods=minor_period).sum()

    denom = sdpos + sdneg
    tii = 100.0 * sdpos / denom.replace(0, float("nan"))
    return tii


def generate_signals(
    price_df: pd.DataFrame,
    major_period: int = 60,
    minor_period: int = 30,
    midline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    tii = _tii(close, major_period, minor_period)
    tii_prev = tii.shift(1)

    entry = ((tii_prev <= midline) & (tii > midline)).fillna(False)
    exit_signal = ((tii_prev > midline) & (tii <= midline)).fillna(False)

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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
