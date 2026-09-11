"""Strategy: Volume-Weighted (typical-price) Moving Average weakness dip-buy
with a FIXED time-stop exit (no crossback condition).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-090):
Per QuantifiedStrategies.com's "Volume Weighted Average Price (VWAP) Trading
Strategy: Backtest and Evaluation"
(https://www.quantifiedstrategies.com/volume-weighted-average-price/,
visited 2026-09-11), the site's own "Strategy 3" backtest on SPY: "When the
close of SPY crosses BELOW the N-day [volume-weighted] moving average, we
sell after N-days" (a pure time-stop exit, not a crossback-above condition)
showed positive average-gain-per-trade across every N tested (5,10,25,50,
100,200), strongest at long holds (N=200 -> 8.66% avg gain/trade) but also
positive at short holds (N=5 -> 0.30%). This is mechanically DISTINCT from
every prior VWMA strategy already tested in this repo:
  - 2026-09-04-060 (accepted): VWMA DUAL crossover (fast vs slow VWMA cross),
    not a single-VWMA weakness dip with fixed time-stop.
  - 2026-09-08-070 (rejected): single-VWMA pullback-BOUNCE continuation
    strategy (requires price bouncing back above VWMA support in an uptrend)
    — the opposite mechanic: this dips INTO weakness on a close crossing
    BELOW, and holds through a fixed period regardless of what price does
    next (no bounce-confirmation required, no crossback-above exit).
  - Also, this VWMA is built on the TYPICAL PRICE (H+L+C)/3, matching the
    source's own VWAP-style construction, rather than plain close as most
    prior repo VWMA variants use.

Signal logic
------------
- Typical price TP = (high + low + close) / 3.
- VWMA[t] = sum(TP[t-w+1..t] * volume[t-w+1..t]) / sum(volume[t-w+1..t])
  (rolling volume-weighted average of typical price over `window` bars).
- Entry (long): close crosses BELOW VWMA (source's "buy on weakness").
- Exit: held for exactly `hold_days` bars, then flat regardless of price
  action (source's own time-stop rule, no crossback condition). No new
  entry can start while already in a position (single-position-at-a-time).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    window: int = 25,
    hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    typical_price = (high + low + close) / 3.0
    tp_vol = typical_price * volume
    vwma = tp_vol.rolling(window).sum() / volume.rolling(window).sum()

    below = close < vwma
    crossed_below = below & (~below.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(crossed_below.iloc[i]):
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
