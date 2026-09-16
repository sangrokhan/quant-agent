"""Strategy: Stochastic Distance Oscillator (SDO) zero-line crossover, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Vitali Apirine's Stochastic Distance Oscillator (SDO), TASC June 2023
"The Stochastic Distance Oscillator", per the MetaQuotes/MQL5 Traders' Tips
code fully disclosed at
https://traders.com/Documentation/FEEDbk_docs/2023/06/TradersTips.html:

- distance[i] = abs(close[i] - close[i - n_periods])
- hh/ll = rolling max/min of `distance` over the trailing `lookback_period`
  bars (default 200)
- perc_d[i] = signed, min-max-normalized distance:
    if close[i] > close[i-n_periods]: +(distance[i]-ll)/(hh-ll)
    if close[i] < close[i-n_periods]: -(distance[i]-ll)/(hh-ll)
    else: 0
- SDO[i] = EMA(perc_d, ema_length) * 100, bounded roughly [-100, 100]

This is a genuinely new construction versus other oscillators already in
this repo: it does not normalize price level (like RSI/Stochastic) but
normalizes the *magnitude of directional price change over a fixed
n_periods lag* against its own rolling extreme range, then signs it by the
direction of that same lagged move. First SDO strategy in this repo (zero
prior strategies_index.jsonl hits for "Stochastic Distance").

Signal logic
------------
- Long entry: SDO crosses above zero AND close > SMA(trend_window) (uptrend
  regime gate, this repo's standard pattern for oscillator-zero-cross
  strategies).
- Exit: SDO crosses back below zero, OR the trend gate flips (close drops
  below the SMA), OR after max_hold_days trading days (time-stop backstop).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
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


def _sdo(close: pd.Series, lookback_period: int, n_periods: int, ema_length: int) -> pd.Series:
    """Vectorized-ish implementation of Apirine's Stochastic Distance Oscillator."""
    distance = (close - close.shift(n_periods)).abs()
    hh = distance.rolling(lookback_period).max()
    ll = distance.rolling(lookback_period).min()
    rng = (hh - ll)

    up_move = close > close.shift(n_periods)
    down_move = close < close.shift(n_periods)

    perc_d = pd.Series(0.0, index=close.index)
    safe_norm = ((distance - ll) / rng.replace(0.0, pd.NA)).fillna(0.0)
    perc_d = perc_d.where(~up_move, safe_norm)
    perc_d = perc_d.where(~down_move, -safe_norm)

    sdo = perc_d.ewm(span=ema_length, adjust=False).mean() * 100.0
    # Blank out the warmup window (matches the source's bar>=length1+length2 guard).
    warmup = lookback_period + n_periods
    sdo.iloc[: min(warmup, len(sdo))] = float("nan")
    return sdo


def generate_signals(
    price_df: pd.DataFrame,
    lookback_period: int = 200,
    n_periods: int = 12,
    ema_length: int = 3,
    trend_window: int = 150,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sdo = _sdo(close, lookback_period, n_periods, ema_length)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    cross_up = (sdo > 0) & (sdo.shift(1) <= 0)
    cross_down = (sdo < 0) & (sdo.shift(1) >= 0)

    entry = cross_up.fillna(False) & uptrend.fillna(False)
    exit_cross = cross_down.fillna(False)
    exit_trend_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_trend_flip.iloc[i]) or held >= max_hold_days:
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
