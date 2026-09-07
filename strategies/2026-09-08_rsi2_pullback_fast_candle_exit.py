"""Strategy: RSI(2) 3-consecutive-extreme-reading pullback with fast candle-high exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-089),
sourced from https://www.mql5.com/en/articles/17636 ("RSI2 Pullback"
strategy, an author's own tweak of Larry Connors' RSI(2) framework).
Concrete rules quoted from the source:

    "The RSI2 Pullback Strategy improves mean-reversion trading by
    requiring several consecutive extreme RSI values... By using RSI2 with
    a slightly higher threshold than the traditional version and combining
    it with three consecutive RSI values above or below that threshold,
    the signal becomes stronger."

    "Buy when: the past three RSI2 value < 10, last close price > 200-period
    moving average, and no current positions."

    "Exit buy when: last close price > second last candle high, or last
    close price < 200-period moving average." -- "This exit idea comes
    from noticing that short-term reversals often show a reversal bar that
    exceeds the prior candle's high or low, allowing us to exit fast and
    lock in a small profit."

Distinct from the already-tested R3 strategy (2026-09-08-087, accepted
SPY) which requires RSI(2) to have DECLINED for 3 consecutive days (a
monotonic-decline precondition, entry level itself only needs to be below
threshold on the LAST day) -- here the requirement is ALL THREE most
recent RSI(2) readings must be below the threshold (an absolute
persistence-in-oversold-zone condition, no monotonic decline required),
and critically the EXIT mechanic is completely different: a fast
candle-high breakout exit (source's own novel contribution) rather than a
recovery-above-a-moving-average exit.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int = 2) -> pd.Series:
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rsi_window: int = 2,
    rsi_threshold: float = 10.0,
    consecutive_bars: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rsi = _rsi(close, rsi_window)
    all_extreme = pd.Series(True, index=close.index)
    for k in range(consecutive_bars):
        all_extreme &= rsi.shift(k) < rsi_threshold

    entry = uptrend.fillna(False) & all_extreme.fillna(False)

    # exit trigger: close > prior bar's high (the "second last candle high"
    # in the source's indexing, since decisions are made after the bar closes)
    prior_high = high.shift(1)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            trend_broken = not bool(uptrend.iloc[i]) if not pd.isna(uptrend.iloc[i]) else False
            fast_exit = (not pd.isna(prior_high.iloc[i])) and close.iloc[i] > prior_high.iloc[i]
            if trend_broken or fast_exit or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_pos = True
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
