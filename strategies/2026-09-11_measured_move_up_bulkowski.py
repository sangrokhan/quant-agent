"""Strategy: Bulkowski Measured Move Up -- buy at the corrective-phase low
after a >=70% retrace of the first leg, target = 60% of the first leg added
to the corrective low.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-023):
Per https://thepatternsite.com/mmu.html (Thomas Bulkowski, visited this
iteration): a Measured Move Up is 3 consecutive confirmed swing turns:
  Point A: a minor (fractal) swing LOW -- start of the first leg.
  Point B: the subsequent minor swing HIGH -- top of the first leg / start
           of the corrective phase.
  Point C: a later minor swing LOW that retraces AT LEAST
           `min_retrace_pct` (source: 0.70, "best measure-rule performance")
           of the A-to-B leg -- end of the corrective phase.
Source's own explicit trading tactic: "Once the second leg begins (point C),
buy. If price drops below the corrective phase low (C), close out the
trade." Target: measure_rule_target = C + `target_pct` * (B - A), where
`target_pct` defaults to the source's own disclosed statistic (0.60 =
the historical "percentage meeting price target"). This repo adds a
max_hold_days safety time-stop since the source gives no explicit time
limit.

Novelty vs existing repo entries: distinct from 1-2-3 Reversal
(2026-09-11-022) -- that pattern enters on a NECKLINE BREAKOUT above Point B
only after an additional Point3 higher-low confirmation, whereas Measured
Move Up enters directly AT Point C (the corrective low itself) as soon as
it's confirmed, with no breakout-above-B requirement. Also distinct from all
double/triple-bottom neckline-breakout strategies already tested (this
pattern's entry point and target formula are both source-specific and
different).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _fractal_extrema(series: pd.Series, lookback: int, kind: str) -> pd.Series:
    n = len(series)
    is_extreme = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(lookback, n - lookback):
        window = vals[i - lookback : i + lookback + 1]
        center = vals[i]
        if np.isnan(center):
            continue
        if kind == "low":
            if center == np.nanmin(window) and np.sum(window == center) == 1:
                is_extreme.iloc[i] = True
        else:
            if center == np.nanmax(window) and np.sum(window == center) == 1:
                is_extreme.iloc[i] = True
    return is_extreme


def generate_signals(
    price_df: pd.DataFrame,
    fractal_lookback: int = 3,
    min_retrace_pct: float = 0.70,
    max_pattern_bars: int = 60,
    target_pct: float = 0.60,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Scans for confirmed swing low A -> swing high B -> swing low C with C
    retracing >= min_retrace_pct of the A-to-B leg. Enters long at the close
    of the bar that confirms C. Exit: close breaks below C (source's own
    stop rule), price reaches the measure-rule target, or max_hold_days.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    swing_low_mask = _fractal_extrema(low, fractal_lookback, "low")
    swing_high_mask = _fractal_extrema(high, fractal_lookback, "high")

    low_idxs = list(np.where(swing_low_mask.values)[0])
    high_idxs = list(np.where(swing_high_mask.values)[0])

    events = []
    for i in low_idxs:
        conf = i + fractal_lookback
        if conf < n:
            events.append((conf, i, "low"))
    for i in high_idxs:
        conf = i + fractal_lookback
        if conf < n:
            events.append((conf, i, "high"))
    events.sort()

    position = pd.Series(0, index=close.index, dtype=int)

    a = None  # (idx, price)
    b = None  # (idx, price)

    in_position = False
    entry_i = None
    stop_level = None
    target_level = None

    ev_pointer = 0

    for i in range(n):
        while ev_pointer < len(events) and events[ev_pointer][0] == i:
            _, swing_i, kind = events[ev_pointer]
            ev_pointer += 1
            price_val = low.iloc[swing_i] if kind == "low" else high.iloc[swing_i]

            if kind == "low":
                if a is not None and b is not None and not in_position:
                    leg = b[1] - a[1]
                    if leg > 0 and swing_i - a[0] <= max_pattern_bars:
                        retrace = (b[1] - price_val) / leg
                        if retrace >= min_retrace_pct:
                            # Point C confirmed -- enter long at this bar's close
                            entry_price = close.iloc[i]
                            stop_level = price_val  # Point C price
                            target_level = price_val + target_pct * leg
                            if target_level > entry_price:
                                in_position = True
                                entry_i = i
                            # reset pattern regardless (used or not, start fresh)
                            a = (swing_i, price_val)
                            b = None
                        else:
                            # not enough retrace -- treat as new A candidate
                            a = (swing_i, price_val)
                            b = None
                    else:
                        # stale or invalid leg -- restart with this as A
                        a = (swing_i, price_val)
                        b = None
                else:
                    # start a fresh A
                    a = (swing_i, price_val)
                    b = None
            else:  # high
                if a is not None and b is None:
                    if swing_i - a[0] <= max_pattern_bars:
                        b = (swing_i, price_val)
                    else:
                        a = None

        if in_position:
            position.iloc[i] = 1
            price = close.iloc[i]
            hold_len = i - entry_i
            if price <= stop_level or price >= target_level or hold_len >= max_hold_days:
                in_position = False
                entry_i = None
                stop_level = None
                target_level = None

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
