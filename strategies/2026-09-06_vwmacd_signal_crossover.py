"""Strategy: Volume-Weighted MACD (VW-MACD) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Rebuilding the classic MACD using Volume-Weighted Moving Averages (VWMA)
instead of plain EMAs makes the fast/slow spread sensitive to participation:
busy (high-volume) bars drag the VWMA lines hard, while thin-volume drift
barely registers, so momentum shifts confirmed by strong volume should be a
higher-conviction signal than the price-only MACD. Per LuxAlgo's Volume-
weighted MACD library page (https://www.luxalgo.com/library/indicator/volume-weighted-macd/):
"subtracts a 26-period slow VWMA from a 12-period fast VWMA, smoothing the
spread with a 9-period signal line -- every close is multiplied by its
volume before averaging"; trading rule: "Signal-line crosses: volume-
weighted momentum turning up or down -- the standard crossover grammar with
participation built in."

First Volume-Weighted-MACD strategy in this repo -- distinct from the
plain-price MACD/PPO variants already tested (2026-09-04-109 PPO,
Percentage Volume Oscillator 2026-09-05-075 which applies MACD construction
to VOLUME itself rather than weighting price by volume) since this replaces
the underlying moving averages' price input with a volume-weighted price,
not a separate volume series.

Signal logic
------------
- VWMA(n) = rolling_sum(close*volume, n) / rolling_sum(volume, n)
- VW-MACD = VWMA(fast_span) - VWMA(slow_span)   (standard 12/26 defaults)
- Signal = EMA(VW-MACD, signal_span)             (standard 9 default)
- Long entry: VW-MACD crosses above Signal.
- Exit: VW-MACD crosses back below Signal, or a max_hold_days time-stop.

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


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, pd.NA)


def _vwmacd(close: pd.Series, volume: pd.Series, fast_span: int, slow_span: int, signal_span: int):
    fast_vwma = _vwma(close, volume, fast_span)
    slow_vwma = _vwma(close, volume, slow_span)
    vwmacd = fast_vwma - slow_vwma
    signal = vwmacd.ewm(span=signal_span, adjust=False).mean()
    return vwmacd, signal


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    vwmacd, signal = _vwmacd(close, volume, fast_span, slow_span, signal_span)
    long_trigger = (vwmacd > signal) & (vwmacd.shift(1) <= signal.shift(1))
    exit_trigger = (vwmacd <= signal) & (vwmacd.shift(1) > signal.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, fast_span=fast_span, slow_span=slow_span,
        signal_span=signal_span, max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
