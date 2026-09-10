"""Strategy: Volume Zone Oscillator (VZO) zero-line crossover, gated by trend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per this iteration's Google SERP synthesis of thinkorswim's VolumeZoneOscillator
study description and Investopedia/TradingView VZO zone semantics (VZO>5% =
positive-trend zone, VZO<-5% = negative-trend zone, +/-40% = extreme
overbought/oversold), and consistent with this repo's own already-tested VZO
formula (id=2026-09-04-122: VZO=100*(VP/TV), VP=EMA of signed OBV-style
volume [close>prior close: +volume, else -volume], TV=EMA of raw volume):
this iteration tests the ZERO-LINE CROSSOVER technique (long when VZO
crosses from <=0 to >0, i.e. the positive/negative trend-zone boundary),
NOT the previously-tested "-40% oversold recovery" mean-reversion technique.
Gated by an SMA(trend_window) trend filter for direction confirmation
(thinkorswim's own guidance: "When the trend mode and direction are
defined, use the crossovers of the VZO with corresponding levels as buy
and sell signals"). Exit on VZO crossing back below zero, the trend filter
breaking, or a max_hold_days time-stop. Distinct from 2026-09-04-122
(rejected: VZO crossing back above -40% oversold level + ADX+EMA(60)
filter, a mean-reversion technique) since this is a trend-following
zero-line-cross technique on the same underlying oscillator.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Both accept keyword-arg tunable parameters per RESEARCH_LOOP.md Step 5.
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


def _vzo(df: pd.DataFrame, vzo_span: int = 14) -> pd.Series:
    close = df["close"]
    volume = df["volume"]
    signed_volume = volume.where(close > close.shift(1), -volume)
    signed_volume = signed_volume.where(close != close.shift(1), 0.0)

    vp = signed_volume.ewm(span=vzo_span, adjust=False).mean()
    tv = volume.ewm(span=vzo_span, adjust=False).mean()
    vzo = 100.0 * (vp / tv.replace(0, np.nan))
    return vzo


def generate_signals(
    price_df: pd.DataFrame,
    vzo_span: int = 14,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vzo = _vzo(df, vzo_span=vzo_span)
    sma_trend = close.rolling(trend_window).mean()
    trend_ok = (close > sma_trend).fillna(False)

    zero_cross_up = ((vzo > 0) & (vzo.shift(1) <= 0)).fillna(False)
    exit_cross_down = (vzo <= 0).fillna(True)

    entry = (zero_cross_up & trend_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross_down.iloc[i]) or not bool(trend_ok.iloc[i]) or held >= max_hold_days:
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
