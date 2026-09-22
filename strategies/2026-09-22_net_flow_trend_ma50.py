"""Strategy: Net Flow Trend (windowed, volume-normalized OBV) + MA50 cross confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-103):
Per ChartCrypto.app's "Net Flow Trend" backtesting strategy page
(https://chartcrypto.app/backtesting/net-flow-trend), FLOW is a windowed
On-Balance-Volume variant: each bar contributes +volume when it closes up
and -volume when it closes down, summed over a rolling `flow_window` (20)
bars and normalized by the average volume over that same window. This
produces a bounded, cross-asset-comparable value (unlike raw cumulative
OBV, whose absolute level is meaningless across symbols/time and requires
an arbitrary EMA-crossover just to extract a signal).

Source's own disclosed rule: "The entry is a 50-bar moving-average break
confirmed by FLOW > 0.5: price crossing up through MA50 while accumulation,
not just price, says the trend is real. The exit mirrors it -- the MA50
cross down or FLOW collapsing below -0.5."

Distinct from every existing OBV-family entry in this repo:
  - 2026-09-04-027 (cumulative OBV vs its own EMA(20) crossover -- unbounded,
    non-comparable OBV level, no rolling-window normalization)
  - 2026-09-04-088 (OBV price-divergence reversal, different mechanic)
  - 2026-09-05-060 (OBV breakout vs its own N-day rolling HIGH, not a
    normalized magnitude threshold)
  - 2026-09-05-078 (OBV-vs-EMA as a gate on an EMA price crossover, not
    MA50, and no windowed-normalization)
This is the first strategy in this repo using a rolling-window,
volume-normalized net-flow value against a FIXED +/-0.5 threshold as the
volume-confirmation signal.

Signal logic
------------
- signed_volume[t] = +volume[t] if close[t] > close[t-1] else -volume[t]
  (0 if unchanged)
- FLOW[t] = sum(signed_volume, flow_window) / mean(volume, flow_window)
- MA50 = SMA(close, ma_window)
- Entry (long): close crosses above MA50 AND FLOW > flow_entry_threshold
  (0.5, source's exact rule) at the crossover bar
- Exit: close crosses below MA50 OR FLOW < flow_exit_threshold (-0.5,
  source's exact mirror rule), backstopped by a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_flow(close: pd.Series, volume: pd.Series, flow_window: int) -> pd.Series:
    price_change = close.diff()
    signed_volume = volume.where(price_change > 0, -volume)
    signed_volume = signed_volume.where(price_change != 0, 0.0)

    flow_sum = signed_volume.rolling(flow_window).sum()
    avg_volume = volume.rolling(flow_window).mean()
    safe_avg = avg_volume.where(avg_volume != 0, 1.0)
    flow = flow_sum / safe_avg
    flow = flow.where(avg_volume != 0, 0.0)
    return flow.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    flow_window: int = 20,
    ma_window: int = 50,
    flow_entry_threshold: float = 0.5,
    flow_exit_threshold: float = -0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    flow = _compute_flow(close, volume, flow_window)
    ma = close.rolling(ma_window).mean()

    above_ma = close > ma
    ma_cross_up = above_ma & (~above_ma.shift(1).fillna(False))
    ma_cross_down = (~above_ma) & (above_ma.shift(1).fillna(False))

    entry_trigger = ma_cross_up & (flow > flow_entry_threshold)
    exit_trigger = ma_cross_down | (flow < flow_exit_threshold)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
