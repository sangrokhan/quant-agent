"""Strategy: WaveTrend Oscillator [LazyBear] overbought/oversold crossover.

Hypothesis (this cron trigger's iteration 4):
Per LazyBear's WaveTrend [WT] indicator (confirmed via GitHub-hosted exact
Pine Script source, https://github.com/bnvnvnv/fmzstrategies/blob/master/
Indicator-WaveTrend-Oscillator.md, source's own default parameters n1=10
channel length / n2=21 average length / obLevel1=60 / osLevel1=-60):
ap = HLC3 (typical price); esa = EMA(ap, n1); d = EMA(|ap-esa|, n1);
ci = (ap-esa) / (0.015*d); tci = EMA(ci, n2); wt1 = tci; wt2 = SMA(wt1, 4).
Source's own disclosed rule (TradingView description + GitHub Pine
strategy block): long entry when wt1 crosses below osLevel1 (deeply
oversold, source default -60) OR crosses back above wt2 from below the
oversold band; exit/short when wt1 crosses above obLevel1 (overbought,
source default 60) or crosses below wt2 from above the overbought band.
This iteration implements the source's disclosed long-only crossover
variant: long entry when wt1 crosses above wt2 while wt1 is below
osLevel1 (a buy confirmation in oversold territory, per Medium's
ALFIL-studios summary: "When the wt1 line crosses above the wt2 line from
below the oversold levels, it may signal a buying opportunity"); exit when
wt1 crosses below wt2 while wt1 is above obLevel1 (mirror sell rule), or a
max_hold_days backstop. Genuinely new indicator family for this repo (0
prior WaveTrend entries).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _wavetrend(high: pd.Series, low: pd.Series, close: pd.Series, n1: int, n2: int):
    ap = (high + low + close) / 3.0
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0.0, np.nan))
    tci = ci.ewm(span=n2, adjust=False).mean()
    wt1 = tci
    wt2 = wt1.rolling(4).mean()
    return wt1, wt2


def generate_signals(
    price_df: pd.DataFrame,
    n1: int = 10,
    n2: int = 21,
    ob_level: float = 60.0,
    os_level: float = -60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    wt1, wt2 = _wavetrend(high, low, close, n1, n2)
    cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))

    entry_signal = cross_up & (wt1 < os_level)
    exit_signal = cross_down & (wt1 > ob_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_hit = bool(exit_signal.iloc[i]) if not pd.isna(exit_signal.iloc[i]) else False
            if exit_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_hit = bool(entry_signal.iloc[i]) if not pd.isna(entry_signal.iloc[i]) else False
            if entry_hit:
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
