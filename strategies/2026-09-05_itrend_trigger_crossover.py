"""Strategy: Ehlers Instantaneous Trendline (iTrend) + Trigger-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-009):
John Ehlers' simplified single-alpha Instantaneous Trendline is a near
zero-lag recursive smoother of price (computed on hl2 per the published
construction). Its "Trigger" line is a lag-reduced projection defined as
2*iTrend_t - iTrend_{t-2} (per LuxAlgo's build of Ehlers' published
recursion). Per LuxAlgo's trading guide, trigger-line crossings are "the
classic entry and exit events": when the Trigger crosses above the
Trendline that is a bullish/long signal (trigger above trendline = long
bias), when it crosses back below that is the exit/short-bias signal.
First Ehlers Instantaneous Trendline strategy in this repo -- distinct
from other Ehlers-family strategies already tested here (MESA Stochastic
id=2026-09-04-118, Center-of-Gravity oscillator id=2026-09-04-124), which
use different Ehlers DSP constructions (cycle-period-based oscillators
vs. this trend-following trendline+trigger pair).

Formula (Ehlers' published simplified single-alpha recursion, as
corroborated by LuxAlgo/alphax.trading -- uses hl2 price and the last two
price points plus the last two trendline values):

  price_t = (high_t + low_t) / 2
  iTrend_t = (alpha - alpha^2/4) * price_t
             + 0.5 * alpha^2 * price_{t-1}
             - (alpha - 0.75 * alpha^2) * price_{t-2}
             + 2 * (1 - alpha) * iTrend_{t-1}
             - (1 - alpha)^2 * iTrend_{t-2}
  (for the first 2 bars, seeded with the hl2 SMA -- Ehlers' own FIR
  warm-up convention)

  Trigger_t = 2 * iTrend_t - iTrend_{t-2}

Signal logic
------------
- Entry (long): Trigger crosses above iTrend (Trigger_t > iTrend_t and
  Trigger_{t-1} <= iTrend_{t-1}).
- Exit: Trigger crosses below iTrend, or a max_hold_days time-stop
  backstop (the source gives no explicit stop rule beyond the crossover
  pair itself).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _itrend_and_trigger(high: pd.Series, low: pd.Series, alpha: float) -> tuple[pd.Series, pd.Series]:
    price = (high + low) / 2.0
    n = len(price)
    itrend = np.zeros(n)
    p = price.to_numpy()

    # Warm-up: first two bars seeded with cumulative hl2 average (Ehlers' FIR warm-up).
    for i in range(min(2, n)):
        itrend[i] = p[: i + 1].mean()

    c1 = alpha - (alpha ** 2) / 4.0
    c2 = 0.5 * (alpha ** 2)
    c3 = alpha - 0.75 * (alpha ** 2)
    c4 = 2.0 * (1.0 - alpha)
    c5 = (1.0 - alpha) ** 2

    for i in range(2, n):
        itrend[i] = (
            c1 * p[i]
            + c2 * p[i - 1]
            - c3 * p[i - 2]
            + c4 * itrend[i - 1]
            - c5 * itrend[i - 2]
        )

    itrend_s = pd.Series(itrend, index=price.index)
    trigger = 2.0 * itrend_s - itrend_s.shift(2)
    trigger.iloc[:2] = itrend_s.iloc[:2]  # no defined trigger yet; treat as flat/no-signal
    return itrend_s, trigger


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.07,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]

    itrend, trigger = _itrend_and_trigger(high, low, alpha)

    above = trigger > itrend
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    position = pd.Series(0, index=itrend.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(itrend)):
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
