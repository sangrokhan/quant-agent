"""Strategy: Ehlers Detrended Synthetic Price (DSP) slope color-change signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-065):
Per https://stonehillforex.com/2023/01/detrended-synthetic-price-as-a-confirmation-indicator/ :
John Ehlers' Detrended Synthetic Price (DSP, Stocks & Commodities, July 2000)
highlights the dominant price cycle by "subtracting a half-cycle EMA from a
quarter-cycle EMA" of a median (hl2) price series. The source's own trading
rule (color-change interpretation, based on the indicator's own math/slope
rather than a zero-line cross): "Long signal -- When the signal line turns
green [DSP rising], entry is made on the open of the next period. Short
signal -- When the signal line turns red [DSP falling], an entry is made on
the open of the next period... using this as an exit is a possibility when
the color turns gray [flat]."

This is a first-time DSP strategy in this repo -- distinct from all prior
Ehlers-family entries (MESA Stochastic id=2026-09-04-118, Center-of-Gravity
id=2026-09-04-124, Instantaneous Trendline/Trigger id=2026-09-05-009,
Decycler Oscillator id=2026-09-05-046, Roofing Filter, Adaptive Laguerre
Filter id=2026-09-05-058) -- DSP's own construction (quarter-cycle minus
half-cycle EMA spread, entered/exited purely on its OWN slope direction
changing) has not been tested here before.

DSP formula (source's own description):
    median_price = (high + low) / 2
    dsp = EMA(median_price, period // 4) - EMA(median_price, period // 2)
Signal color: green when dsp is rising (dsp > dsp.shift(1)), red when
falling, otherwise flat/gray (treated as no-signal/exit zone, per source's
own note it "may make a good exit indicator").

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


def _dsp(df: pd.DataFrame, period: int = 14) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    quarter = max(2, period // 4)
    half = max(3, period // 2)
    ema_quarter = median_price.ewm(span=quarter, adjust=False).mean()
    ema_half = median_price.ewm(span=half, adjust=False).mean()
    return ema_quarter - ema_half


def generate_signals(
    price_df: pd.DataFrame,
    dsp_period: int = 14,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: DSP color turns green (was not rising, now rising --
    dsp(t) > dsp(t-1) while dsp(t-1) <= dsp(t-2)).
    Exit: color turns gray/flat-or-falling (dsp(t) <= dsp(t-1)), or a
    max_hold_days time-stop (source has no explicit stop; add one for
    safety per this repo's convention).
    """
    df = _prep(price_df)
    dsp = _dsp(df, period=dsp_period)

    rising = dsp > dsp.shift(1)
    was_rising = dsp.shift(1) > dsp.shift(2)

    turned_green = rising & (~was_rising.fillna(False))
    turned_not_green = ~rising  # gray or red -> exit

    position = pd.Series(0, index=dsp.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(dsp)):
        if in_position:
            hold_days += 1
            if bool(turned_not_green.iloc[i]) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(turned_green.iloc[i]):
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
