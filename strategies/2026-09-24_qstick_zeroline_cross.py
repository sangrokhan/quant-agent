"""Strategy: Qstick zero-line-cross trend-following, EMA trend filter, RSI
overbought guard (long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per ArrowAlgo's Qstick Indicator Complete Guide
(https://arrowalgo.com/qstick-indicator-complete-guide-algorithmic-trading/):
the Qstick indicator (Richard W. Arms Jr.) is an SMA of (close-open) per
candle over a lookback window -- a pure "who won each session's battle
between buyers and sellers" momentum reading, distinct from every
close-to-close momentum indicator (RSI/MACD/ROC) already in this repo
because it measures INTRA-BAR directional conviction (close vs that same
bar's open), not bar-to-bar price change. The source's own "Zero-Line
Cross Strategy": enter long when Qstick crosses above zero AND price holds
above a key EMA (confirms momentum+trend at once); exit when Qstick
crosses back below zero; the source also recommends an RSI overbought
guard to avoid entering into an already-extended move. First Qstick entry
in this repo (0 prior KB hits).

Signal logic (long side only)
------------------------------
- Qstick: SMA(close - open, qstick_period).
- Entry: Qstick crosses above 0 (Qstick_t > 0 AND Qstick_{t-1} <= 0) AND
  close > EMA(ema_period) (trend confirmation) AND RSI(rsi_period) <
  rsi_overbought_guard (avoid overbought entries per source's own stated
  mistake-avoidance rule).
- Exit: Qstick crosses back below 0, OR close falls below the EMA (trend
  break), OR `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    qstick_period: int = 8,
    ema_period: int = 50,
    rsi_period: int = 14,
    rsi_overbought_guard: float = 70.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    n = len(df)

    qstick = (close - open_).rolling(qstick_period).mean()
    ema = close.ewm(span=ema_period, adjust=False).mean()
    rsi = _rsi(close, rsi_period)

    qstick_above = (qstick > 0).fillna(False)
    cross_up = qstick_above & (~qstick_above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_cond = (not bool(qstick_above.iloc[i])) or (close.iloc[i] < ema.iloc[i]) or (held >= max_hold_days)
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(cross_up.iloc[i]) and close.iloc[i] > ema.iloc[i] and rsi.iloc[i] < rsi_overbought_guard:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
