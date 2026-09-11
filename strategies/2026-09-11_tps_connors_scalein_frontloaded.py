"""Strategy: TPS Connors scale-in, FRONT-LOADED weight schedule variant.

Hypothesis (knowledge_base id=2026-09-11-098):
Direct follow-up to the flagged-for-revisit near-miss 2026-09-06-185 (TPS
Connors scale-in, QQQ full-sample Sharpe 0.871, MDD only 0.070, param
sensitivity extremely stable 0.086, walk-forward 4/4 -- rejected purely on
the 1.0 Sharpe threshold by a narrow margin). Its own log notes flagged it
"worth revisiting: try steeper scale-in weights ... or a higher position
cap to capture more upside". A prior iteration (2026-09-06-186) already
tried a BACK-loaded steeper schedule (10/25/35/50, i.e. MORE weight added
on later, deeper pullback days) and that made things WORSE, not better.

This iteration tests the opposite, unexplored direction: a FRONT-loaded
schedule (40/30/20/10, i.e. commit MORE size on the initial entry and less
on subsequent scale-in days) under the reasoning that 2026-09-06-185's own
grid found the edge concentrated in the HIGH-vol regime (unusual vs. most
strategies in this repo, which concentrate in low-vol) -- in a genuine
high-vol oversold bounce, waiting to scale in on further weakness (the
original back-loaded design) may mean missing much of the bounce if the
reversal happens fast, whereas committing size earlier should capture more
of a sharp V-shaped recovery. Same trend filter/RSI entry-exit trigger
mechanics as 2026-09-06-185/186, only the weight schedule differs.

Interface note: generate_signals returns a fractional weight Series in
[0, 1] (same non-binary position-sizing mechanic as the parent strategy).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_ema_window: int = 200,
    rsi_window: int = 2,
    rsi_entry_threshold: float = 25.0,
    rsi_exit_threshold: float = 70.0,
    scale_in_weights: tuple = (0.40, 0.30, 0.20, 0.10),
    max_scale_in_days: int = 3,
) -> pd.Series:
    """Return a fractional [0,1] position-weight series (front-loaded)."""
    df = _prep(price_df)
    close = df["close"]

    trend_ema = close.ewm(span=trend_ema_window, adjust=False).mean()
    uptrend = close > trend_ema

    rsi = _rsi(close, rsi_window)
    oversold_2day = (rsi < rsi_entry_threshold) & (rsi.shift(1) < rsi_entry_threshold)
    entry_trigger = (oversold_2day & uptrend).fillna(False)
    exit_trigger = (rsi > rsi_exit_threshold).fillna(False)

    weight = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    current_weight = 0.0
    last_entry_price = None
    scale_ins_done = 0

    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                current_weight = 0.0
                last_entry_price = None
                scale_ins_done = 0
                weight.iloc[i] = 0.0
                continue
            if scale_ins_done < max_scale_in_days and (last_entry_price is not None) and px < last_entry_price:
                current_weight = min(1.0, current_weight + scale_in_weights[scale_ins_done + 1])
                last_entry_price = px
                scale_ins_done += 1
            weight.iloc[i] = current_weight
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                current_weight = scale_in_weights[0]
                last_entry_price = px
                scale_ins_done = 0
                weight.iloc[i] = current_weight
            else:
                weight.iloc[i] = 0.0
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret
