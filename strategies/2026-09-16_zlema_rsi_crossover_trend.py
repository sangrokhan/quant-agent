"""Strategy: ZLEMA-smoothed RSI dual-line crossover (Vervoort NPR21 concept),
gated by a long-term EMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-16-XXX):
Per https://theindicatorlab.com/reviews/vervoortcrossover-zero-lag-npr21/
(review of "VervoortCrossover Zero Lag NPR21", a Pine Script port of Sylvain
Vervoort's zero-lag RSI crossover concept originally published in Stocks &
Commodities, 2009): take a base-period RSI (default 21), apply a Zero-Lag
EMA (ZLEMA) smoothing to it to get a "fast" line, then apply a second ZLEMA
smoothing to that fast line to get a "slow" signal line. Because ZLEMA
de-lags via a lag-correction term (2*x - x.shift(lag)) before the EMA, the
fast/slow RSI lines cross 2-4 bars earlier than a standard RSI-crossover or
MACD, per the source's own before/after chart comparison.

This is DISTINCT from this repo's prior ZLEMA entries (2026-09-04-066 plain
price ZLEMA dual crossover, 2026-09-06-170/171 ZLEMA/EMA + slope filter) --
those apply ZLEMA to raw PRICE. This iteration applies ZLEMA to RSI (an
oscillator), a different base series entirely, and combines it with the
source's own recommended overbought/oversold gate (only take long crosses
below 70) plus its recommended 200-period trend filter (only trade long
above the long-term EMA -- source says this "cut false signals by about
40%").

Signal logic
------------
- RSI(rsi_period) computed on close.
- fast_line = ZLEMA(RSI, fast_len); slow_line = ZLEMA(fast_line, slow_len)
  (ZLEMA(x, span): lag = (span-1)//2, de_lagged = 2*x - x.shift(lag),
  then EMA(de_lagged, span)).
- Long entry: fast_line crosses above slow_line AND fast_line < overbought
  AND close > EMA(trend_window) (source's 200-EMA trend filter).
- Exit: fast_line crosses back below slow_line, OR close falls back below
  EMA(trend_window) (trend flip), OR a max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _zlema(series: pd.Series, span: int) -> pd.Series:
    lag = max(1, (span - 1) // 2)
    de_lagged = 2.0 * series - series.shift(lag)
    return de_lagged.ewm(span=span, adjust=False, min_periods=span).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 21,
    fast_len: int = 3,
    slow_len: int = 10,
    overbought: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_period)
    fast_line = _zlema(rsi, fast_len)
    slow_line = _zlema(fast_line, slow_len)

    trend_ema = close.ewm(span=trend_window, adjust=False, min_periods=trend_window).mean()
    trend_long = close > trend_ema

    cross_up = (fast_line > slow_line) & (fast_line.shift(1) <= slow_line.shift(1))
    cross_down = (fast_line < slow_line) & (fast_line.shift(1) >= slow_line.shift(1))

    entry = cross_up & (fast_line < overbought) & trend_long.fillna(False)
    exit_cross = cross_down
    exit_trend = ~trend_long.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            # min_hold_days hysteresis: suppress the crossover-exit signal
            # (but not the trend-flip exit) for the first N days after entry
            # -- same fix pattern as Klinger 2026-09-04-085 / ZLEMA 2026-09-06-171.
            crossover_exit_ok = bool(exit_cross.iloc[i]) and held >= min_hold_days
            if crossover_exit_ok or bool(exit_trend.iloc[i]) or held >= max_hold_days:
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
