"""Strategy: Chande Kroll Stop trend-following breakout/exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-215):
Per this iteration's research (Google AI-overview synthesis, browser_exec
Google SERP fallback -- web_search DDGS backend erroring with TLS
RequestError on every query attempted this iteration), the Chande Kroll
Stop (Tushar Chande & Stanley Kroll) constructs a pair of ATR-based
volatility-adaptive stop lines:

    long_stop_raw  = HighestHigh(p) - x * ATR(p)
    short_stop_raw = LowestLow(p)   + x * ATR(p)
    long_stop      = long_stop_raw.rolling(q).max()   (smoothed "low stop" line)
    short_stop     = short_stop_raw.rolling(q).min()  (smoothed "high stop" line)

Default disclosed parameters: p (ATR period) = 10, x (ATR multiplier) = 1.0,
q (smoothing period) = 9. Trading rule (per TrendSpider/Definedge Securities,
corroborated by the AI overview): long entry when close crosses above the
short_stop ("upper"/high-stop line, i.e. price breaks decisively above
recent resistance-adjusted-for-volatility), gated by a trend filter (a
21-period SMA uptrend confirmation is one commonly cited variant); exit
(go flat) when close crosses back below the long_stop line, signaling
trend exhaustion/a trailing-stop hit.

This is the first Chande Kroll Stop strategy in this repo (novelty checked
against strategies_index.jsonl -- no prior "chande kroll"/"kroll stop"
entries; distinct from this repo's existing Chandelier Exit strategies,
which use a single ATR-trailing-stop off the highest high only, not this
indicator's dual smoothed high/low ATR-offset band pair).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  {0,1} position series
    generate_returns(price_df, **params) -> pd.Series  daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    atr_mult: float = 1.0,
    smooth_period: int = 9,
    trend_window: int = 21,
    use_trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(high, low, close, atr_period)
    highest_high = high.rolling(atr_period).max()
    lowest_low = low.rolling(atr_period).min()

    long_stop_raw = highest_high - atr_mult * atr
    short_stop_raw = lowest_low + atr_mult * atr

    long_stop = long_stop_raw.rolling(smooth_period).max()
    short_stop = short_stop_raw.rolling(smooth_period).min()

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = (close > trend_sma) if use_trend_filter else pd.Series(True, index=close.index)

    entry = (close > short_stop) & trend_ok.fillna(False)
    exit_signal = close < long_stop

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]) if not pd.isna(exit_signal.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False:
                in_position = True
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
