"""Strategy: Donchian/SMA breakout confirmed by a rising Percentage Volume
Oscillator (PVO), per StockCharts ChartSchool's own disclosed formula and
"validating breaks" interpretation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-111):
Per StockCharts ChartSchool (https://chartschool.stockcharts.com/table-of-
contents/technical-indicators-and-overlays/technical-indicators/percentage-
volume-oscillator-pvo, formula PVO = (EMA12(vol) - EMA26(vol)) /
EMA26(vol) * 100, signal = EMA9(PVO)): "a support break on increasing
volume has more credibility than a support break on low volume...a
resistance break on expanding volume shows more buying interest,
increasing the chances of success." First PVO-based strategy in this
repo (distinct from OBV/CMF/MFI/Klinger and other volume oscillators
already tested). Long entry: close breaks above its own N-day rolling
high (Donchian-style breakout) AND PVO is positive and rising (crossing
above its own signal line), confirming the breakout with above-average,
increasing volume per the source's own validation heuristic. Exit on a
Donchian-low breakdown or a max holding period.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pvo(volume: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = volume.ewm(span=fast, adjust=False).mean()
    ema_slow = volume.ewm(span=slow, adjust=False).mean()
    pvo = (ema_fast - ema_slow) / ema_slow.replace(0.0, pd.NA) * 100.0
    pvo_signal = pvo.ewm(span=signal, adjust=False).mean()
    return pvo, pvo_signal


def generate_signals(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    pvo_fast: int = 12,
    pvo_slow: int = 26,
    pvo_signal: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series: Donchian breakout entry
    confirmed by positive+rising PVO (crossing above its own signal line),
    exit on Donchian-low breakdown or max_hold_days time-stop."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]

    rolling_high = close.rolling(breakout_window).max().shift(1)
    rolling_low = close.rolling(breakout_window).min().shift(1)

    pvo, pvo_sig = _pvo(volume, pvo_fast, pvo_slow, pvo_signal)
    pvo_confirms = (pvo > 0) & (pvo > pvo_sig)

    breakout_up = close > rolling_high
    breakdown = close < rolling_low

    entry = breakout_up.fillna(False) & pvo_confirms.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(breakdown.iloc[i]) or held >= max_hold_days:
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
