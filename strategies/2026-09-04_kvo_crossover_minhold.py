"""Strategy: Klinger Volume Oscillator (KVO) crossover with EMA trend filter
AND a minimum-holding-period whipsaw filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-085):
The KVO signal-line-crossover + EMA-trend-filter strategy (2026-09-04-084)
had genuinely good signal quality (equity grid pass_fraction 0.292, best
single-cell Sharpe 1.79, primary-config Sharpe 1.111 clearing the 1.0
threshold) but was REJECTED because its raw trade frequency (350
round-trips over 7.7yr) fails transaction-cost-survival once 10bps/trade
costs are applied, and every attempt to reduce frequency via additional
EMA smoothing degraded the underlying signal faster than it cut costs.
Per general whipsaw-reduction guidance (tradinggenie.ai/quantt.co.uk: "a
minimum separation between crossover signals" is a standard technique
distinct from smoothing), this variant adds an explicit
`min_hold_days` gate: once a position is entered, exit signals are
ignored for the first N days regardless of what the oscillator does,
directly targeting the trade-COUNT problem rather than blunting the
oscillator's underlying sensitivity.

Signal logic
------------
Identical KVO/signal-line/EMA-trend-filter construction as
2026-09-04_klinger_volume_oscillator_crossover.py, with one addition:
- Once in a position, exit signals (KVO cross-down OR trend-filter break)
  are IGNORED until at least `min_hold_days` trading days have elapsed
  since entry. After that, normal exit logic applies.

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


def _compute_kvo(df: pd.DataFrame, fast_span: int, slow_span: int, signal_span: int):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    hlc_sum = high + low + close
    trend = np.sign(hlc_sum.diff()).replace(0, np.nan).ffill().fillna(1.0)

    hl_range = (high - low).replace(0, np.nan)
    dm = ((close - low) - (high - close)) / hl_range
    dm = dm.fillna(0.0)
    volume_force = volume * trend * (2 * dm).abs() * 100

    kvo = volume_force.ewm(span=fast_span, adjust=False).mean() - volume_force.ewm(
        span=slow_span, adjust=False
    ).mean()
    signal_line = kvo.ewm(span=signal_span, adjust=False).mean()
    return kvo, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 21,
    slow_span: int = 45,
    signal_span: int = 13,
    ema_window: int = 100,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kvo, signal_line = _compute_kvo(df, fast_span, slow_span, signal_span)
    ema_trend = close.ewm(span=ema_window, adjust=False).mean()

    above_signal = kvo > signal_line
    above_signal_prev = above_signal.shift(1)
    cross_up = above_signal & (~above_signal_prev.fillna(False))
    cross_down = (~above_signal) & (above_signal_prev.fillna(False))

    above_trend = close > ema_trend

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_trigger = bool(cross_down.iloc[i]) or not bool(above_trend.iloc[i])
            if exit_trigger and hold_count >= min_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(above_trend.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_span: int = 21,
    slow_span: int = 45,
    signal_span: int = 13,
    ema_window: int = 100,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        fast_span=fast_span,
        slow_span=slow_span,
        signal_span=signal_span,
        ema_window=ema_window,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
