"""Strategy: Stochastic Pop (Bernstein/Steckler, StockCharts version) --
dual-period Stochastic bias + ADX range filter + volume-confirmed pop.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "Stochastic Pop and Drop"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/stochastic-pop-and-drop,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; original technique by Jake Bernstein, modified by
David Steckler, S&C Magazine Aug 2000): a three-stage mechanical system --
(1) TRADING BIAS: a long-period (70-day, StockCharts' own daily-chart
substitute for Steckler's original 14-week Stochastic) Stochastic %K above
50 defines a bullish regime; (2) RANGE DETECTION: ADX(14) below a threshold
(20, tightened to 15 per the source's own "indicator tweaks" note for
higher precision) signals the trend has slowed into a consolidation/range,
the setup phase; (3) POP TRIGGER: while both above hold, a short-period
(14-day) Stochastic %K surging above 80 WITH volume above its own 250-day
average (source's own disclosed "compare current volume to the 250-day
moving average... volume above the one-year average would be deemed
strong") triggers the long entry. Exit when the short Stochastic later
drops back below 50 (source's own stated momentum-stall exit: "The 14-day
Stochastic Oscillator can also be used to define a stall or downturn in
short-term momentum. A move below 50 signals a momentum shift").

This is a genuinely distinct construction from this repo's existing
"Stochastic Pop" entry (2026-09-17-186, sourced from a Reddit/r-pinescript
post: EMA-smoothed raw %K crossing non-standard 55/45 bands with reset
hysteresis, gated by an EMA200 rising-trend filter, NO ADX range-detection
stage and NO volume confirmation at all) -- this StockCharts/
Bernstein-Steckler version instead requires (a) a long-period Stochastic
BIAS filter, (b) an explicit ADX-based RANGE/consolidation detection stage
before the pop can trigger, and (c) a VOLUME confirmation on the pop bar
itself, none of which exist in the already-tested variant.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
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


def _stochastic_k(df: pd.DataFrame, window: int) -> pd.Series:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    denom = (high_max - low_min).replace(0, np.nan)
    k = 100.0 * (df["close"] - low_min) / denom
    return k.fillna(50.0)


def _adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / window, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False).mean()
    return adx.fillna(0.0)


def _core(
    price_df: pd.DataFrame,
    bias_window: int = 70,
    bias_level: float = 50.0,
    adx_window: int = 14,
    adx_max: float = 20.0,
    pop_window: int = 14,
    pop_level: float = 80.0,
    exit_level: float = 50.0,
    vol_avg_window: int = 250,
) -> pd.Series:
    df = _prep(price_df)
    bias_k = _stochastic_k(df, bias_window)
    pop_k = _stochastic_k(df, pop_window)
    adx = _adx(df, adx_window)
    vol_avg = df["volume"].rolling(vol_avg_window).mean()

    bullish_bias = bias_k > bias_level
    ranging = adx < adx_max
    pop_trigger = (pop_k > pop_level) & (df["volume"] > vol_avg)
    exit_signal = pop_k < exit_level

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(len(df)):
        if in_pos:
            if bool(exit_signal.iloc[i]):
                in_pos = False
            else:
                position.iloc[i] = 1
        else:
            if bool(bullish_bias.iloc[i]) and bool(ranging.iloc[i]) and bool(pop_trigger.iloc[i]):
                in_pos = True
                position.iloc[i] = 1
    return position


def generate_signals(
    price_df: pd.DataFrame,
    bias_window: int = 70,
    bias_level: float = 50.0,
    adx_window: int = 14,
    adx_max: float = 20.0,
    pop_window: int = 14,
    pop_level: float = 80.0,
    exit_level: float = 50.0,
    vol_avg_window: int = 250,
) -> pd.Series:
    return _core(
        price_df, bias_window, bias_level, adx_window, adx_max,
        pop_window, pop_level, exit_level, vol_avg_window,
    )


def generate_returns(
    price_df: pd.DataFrame,
    bias_window: int = 70,
    bias_level: float = 50.0,
    adx_window: int = 14,
    adx_max: float = 20.0,
    pop_window: int = 14,
    pop_level: float = 80.0,
    exit_level: float = 50.0,
    vol_avg_window: int = 250,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(
        df, bias_window, bias_level, adx_window, adx_max,
        pop_window, pop_level, exit_level, vol_avg_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return daily_ret * position.shift(1).fillna(0)
