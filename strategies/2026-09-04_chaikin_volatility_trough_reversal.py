"""Strategy: Chaikin Volatility trough-reversal with SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-133):
Marc Chaikin's Volatility indicator (CV) measures the percentage rate of
change of an EMA-smoothed high-low range over a lookback window:
CV = 100 * (EMA(High-Low, ema_period) - EMA(High-Low, ema_period) roc_period
bars ago) / EMA(High-Low, ema_period) roc_period bars ago. Per
[trendspider.com](https://trendspider.com/learning-center/chaikin-volatility/):
"a trader might enter a long position when the indicator rises from a low
value, suggesting that an increase in volatility could lead to a bullish
price movement... exit ... when the indicator begins to fall from a high
value." Since CV itself carries no directional information (it only
measures range expansion/contraction), this is combined with GoCharting's
own recommendation to "always pair with a directional indicator for
entry" -- operationalized here as a trend-following SMA filter (close
above a trend_window SMA). Long entry: CV was near a trailing-window low
(bottom pctile_threshold percentile over lookback_window bars) and then
turns up (first up-tick), AND price is above the trend SMA. Exit: CV turns
down from near a trailing-window high (top pctile_threshold percentile),
OR a max_hold_days time-stop. First Chaikin Volatility strategy tested in
this repo -- distinct from all prior volatility-regime filters (ATR bands,
Bollinger Band width, realized-vol terciles) since CV specifically
measures the rate of change of an EMA-smoothed high-low range rather than
a raw range or standard deviation.

Signal logic
------------
- ema_period: EMA smoothing period for the high-low range (default 10).
- roc_period: lookback for the rate-of-change comparison (default 10).
- lookback_window: window used to rank CV into percentiles (default 60).
- pctile_threshold: percentile band width for "low"/"high" CV zones
  (default 20, i.e. bottom/top 20%).
- trend_window: SMA period for the directional trend filter (default 100).
- Long entry: CV in bottom pctile_threshold% of lookback_window AND CV
  turns up (CV > CV.shift(1)) AND close > trend SMA.
- Exit: CV in top pctile_threshold% of lookback_window AND CV turns down
  (CV < CV.shift(1)), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _chaikin_volatility(df: pd.DataFrame, ema_period: int, roc_period: int) -> pd.Series:
    hl_range = df["high"] - df["low"]
    ema_range = hl_range.ewm(span=ema_period, adjust=False).mean()
    cv = 100 * (ema_range - ema_range.shift(roc_period)) / ema_range.shift(roc_period)
    return cv


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 10,
    roc_period: int = 10,
    lookback_window: int = 60,
    pctile_threshold: float = 20.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cv = _chaikin_volatility(df, ema_period, roc_period)
    cv_low_thresh = cv.rolling(lookback_window).quantile(pctile_threshold / 100.0)
    cv_high_thresh = cv.rolling(lookback_window).quantile(1 - pctile_threshold / 100.0)

    near_low = cv <= cv_low_thresh
    near_high = cv >= cv_high_thresh
    cv_turning_up = cv > cv.shift(1)
    cv_turning_down = cv < cv.shift(1)

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    entry_signal = near_low & cv_turning_up & trend_ok
    exit_signal = near_high & cv_turning_down

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_period: int = 10,
    roc_period: int = 10,
    lookback_window: int = 60,
    pctile_threshold: float = 20.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        ema_period=ema_period,
        roc_period=roc_period,
        lookback_window=lookback_window,
        pctile_threshold=pctile_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
