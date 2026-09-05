"""Strategy: Volume Price Trend (VPT) signal-line crossover, gated by a
longer-term uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-076):
Volume Price Trend (VPT, also called Price Volume Trend/PVT) is a
cumulative volume line where each bar adds that bar's volume multiplied by
the day's percentage price change: VPT_t = VPT_{t-1} + volume_t *
(close_t - close_{t-1}) / close_{t-1}. Per multiple convergent sources
(LuxAlgo's definition + a Facebook trading-community post on VPT signal-
line crossovers): "A signal line, which is just a moving average of the
indicator, can be used" for entries/exits -- the standard MACD-like
crossover interpretation. VPT crossing above its own signal line (a rolling
average of VPT) signals building buying pressure worth a long entry, gated
by close > SMA(trend_window) (this repo's standard oscillator-uptrend-gate
convention). Distinct from OBV (raw +/- volume accumulation based only on
the SIGN of the daily price change) -- VPT weights each day's volume
contribution by the MAGNITUDE of that day's percentage price move, not just
its direction, making it a genuinely different volume-accumulation
construction. First VPT/PVT strategy in this repo.

Signal logic
------------
- VPT = cumulative sum of volume * daily pct-change in close.
- Signal = SMA(signal_window, VPT).
- Entry (long): VPT crosses above Signal AND close > SMA(trend_window)
  (uptrend gate).
- Exit: VPT crosses back below Signal, the trend filter breaks, or a
  max_hold_days time-stop.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    signal_window: int = 21,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    pct_change = close.pct_change().fillna(0.0)
    vpt = (volume * pct_change).cumsum()
    signal = vpt.rolling(signal_window).mean()

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    bull_cross = (vpt > signal) & (vpt.shift(1) <= signal.shift(1))
    bear_cross = (vpt < signal) & (vpt.shift(1) >= signal.shift(1))

    entry = bull_cross.fillna(False) & uptrend.fillna(False)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bear_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
