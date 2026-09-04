"""Strategy: Price and Volume Trend (PVT) crossing its own EMA signal line.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-101):
PVT (Price and Volume Trend) = cumulative sum of (daily pct price change *
volume) -- a running total that weights each day's volume by the magnitude
of that day's percentage price move (distinct from OBV's sign-only weighting
and CMF/A-D-line's intrabar-position weighting). Per TradingView/Medium/FMZ
sources: compute an EMA of the PVT line itself as a signal line; long entry
when PVT crosses above its own EMA (rising money-flow momentum), exit when
PVT crosses back below its EMA. quantifiedstrategies.com's own specific
82%-win-rate numeric backtest rule is paywalled, so this free crossover
variant is implemented instead, with this repo's standard 200d SMA trend
filter added per convention.

Signal logic
------------
- PVT[t] = PVT[t-1] + (close[t]/close[t-1] - 1) * volume[t], PVT[0] = 0.
- PVT_EMA[t] = EMA(pvt_ema_window, PVT).
- Entry: PVT[t] crosses above PVT_EMA[t] (PVT[t] > PVT_EMA[t] AND
  PVT[t-1] <= PVT_EMA[t-1]) AND close[t] > SMA(trend_window)[t] (uptrend
  filter, per repo convention).
- Exit: PVT[t] crosses below PVT_EMA[t] (PVT[t] < PVT_EMA[t] AND
  PVT[t-1] >= PVT_EMA[t-1]), or trend filter breaks (close < SMA), or after
  max_hold_days.
- Flat otherwise. Long-only per SAFETY.md.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pvt(close: pd.Series, volume: pd.Series) -> pd.Series:
    pct_change = close.pct_change().fillna(0.0)
    daily_contribution = pct_change * volume
    return daily_contribution.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    pvt_ema_window: int = 21,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]

    pvt = _pvt(close, volume)
    pvt_ema = pvt.ewm(span=pvt_ema_window, adjust=False).mean()
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    pvt_above = pvt > pvt_ema
    cross_up = pvt_above & (~pvt_above.shift(1).fillna(False))
    cross_down = (~pvt_above) & (pvt_above.shift(1).fillna(False))

    uptrend = (close > trend_sma).fillna(False)
    entry = cross_up & uptrend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(cross_down.iloc[i]) or (not bool(uptrend.iloc[i])) or held >= max_hold_days
            if exit_now:
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
