"""Strategy: Stochastic RSI (StochRSI) oversold-zone %K/%D crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-078):
StochRSI (Tushar Chande & Stanley Kroll, 1994) applies the stochastic
oscillator formula to RSI values instead of raw price, producing a more
sensitive/faster-moving 0-1 (or 0-100 scaled) momentum measure than plain
RSI, with tighter overbought/oversold bands (>0.8 / <0.2 vs RSI's 70/30).
Per QuantifiedStrategies.com's own SPY backtest (78% win rate, 228 trades,
MDD 15%) and per navia.co.in's concrete crossover rule: a bullish entry
signal fires when %K crosses above %D while both are BELOW the 20%
oversold threshold (not a raw unconditional crossover, which the source
notes underperforms). Exit when %K crosses below %D while above the 80%
overbought threshold (symmetric exit), or (long-only variant here) simply
when %K crosses back below %D. Distinct from plain Stochastic (already
tested at 2026-09-04-028, applies the stochastic formula to PRICE) and
from RSI2/RSI-divergence (raw RSI, not a stochastic-of-RSI double
transform).

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _stoch_rsi(close: pd.Series, rsi_window: int, stoch_window: int, smooth_k: int, smooth_d: int):
    rsi = _rsi(close, rsi_window)
    rsi_min = rsi.rolling(stoch_window).min()
    rsi_max = rsi.rolling(stoch_window).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100.0
    k = stoch_rsi.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    stoch_window: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: %K crosses above %D while both are below ``oversold``.
    Exit: %K crosses below %D (regardless of zone -- the classic long-only
    take-profit-on-momentum-fade exit).
    """
    df = _prep(price_df)
    close = df["close"]
    k, d = _stoch_rsi(close, rsi_window, stoch_window, smooth_k, smooth_d)

    cross_up = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold) & (d < oversold)
    cross_down = (k < d) & (k.shift(1) >= d.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(cross_down.iloc[i]) if not pd.isna(cross_down.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
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
