"""Strategy: Chaikin Volatility (CHV) expansion spike with trend/RSI confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-078):
Per a Google AI-overview synthesis (cTrader/Enlightened Stock Trading/
TrendSpider; browser_exec fallback -- web_search DDGS backend returns
mangled non-English results this iteration), the Chaikin Volatility
indicator (Mark Chaikin) measures the rate-of-change of an EMA of the
high-low spread -- a rising CHV signals expanding volatility/participation
(often at trend starts or capitulation events), while CHV itself is
direction-blind (like VHF, 2026-09-20-077, but measuring range-EXPANSION
rate rather than net-displacement-over-path-length). The disclosed rule
combines a CHV expansion spike with directional confirmation: long entry
when CHV rises sharply (above a z-scored threshold vs its own trailing
distribution) AND price is above a 50-day SMA trend filter AND RSI(14) is
above 50 (momentum confirmation); exit when CHV rolls over (falls below its
own short SMA) or price closes below the SMA trend filter. First Chaikin
Volatility strategy in this repo (0 prior hits in strategies_index.jsonl) --
distinct from every other volatility-based strategy here since none uses a
rate-of-change-of-range-EMA construction.

CHV formula (standard, Mark Chaikin):
    spread_ema = EMA(High - Low, spread_period)
    CHV = 100 * (spread_ema - spread_ema.shift(roc_period)) / spread_ema.shift(roc_period)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _chv(df: pd.DataFrame, spread_period: int = 10, roc_period: int = 10) -> pd.Series:
    spread = df["high"] - df["low"]
    spread_ema = spread.ewm(span=spread_period, adjust=False).mean()
    chv = 100.0 * (spread_ema - spread_ema.shift(roc_period)) / spread_ema.shift(roc_period).replace(0, pd.NA)
    return chv


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    spread_period: int = 10,
    roc_period: int = 10,
    chv_zscore_window: int = 60,
    chv_zscore_threshold: float = 1.0,
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: CHV's rolling z-score exceeds `chv_zscore_threshold`
    (volatility-expansion spike) AND close > SMA(trend_window) (trend
    filter) AND RSI(14) > 50 (momentum confirmation). Exit: close falls
    back below SMA(trend_window), or CHV's z-score rolls back below 0
    (volatility contraction, momentum spent).
    """
    df = _prep(price_df)
    close = df["close"]

    chv = _chv(df, spread_period=spread_period, roc_period=roc_period)
    chv_mean = chv.rolling(chv_zscore_window).mean()
    chv_std = chv.rolling(chv_zscore_window).std()
    chv_z = (chv - chv_mean) / chv_std.replace(0, pd.NA)

    trend_sma = close.rolling(trend_window).mean()
    rsi = _rsi(close, period=14)

    entry = (chv_z > chv_zscore_threshold) & (close > trend_sma) & (rsi > 50)
    stay = (close > trend_sma) & (chv_z > 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.fillna(False).values
    stay_vals = stay.fillna(False).values

    for i in range(len(close)):
        if in_position:
            if not bool(stay_vals[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
