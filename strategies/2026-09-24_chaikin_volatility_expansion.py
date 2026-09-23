"""Strategy: Chaikin Volatility expansion breakout + SMA/RSI trend
confirmation (long only), adapted from a standard EMA-of-HL-range
"volatility expansion after contraction" trading rule.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per enlightenedstocktrading.com's Chaikin Volatility Indicator guide
(https://enlightenedstocktrading.com/chaikin-volatility-indicator/): the
Chaikin Volatility Indicator (Marc Chaikin) is the percent change of an
EMA of the daily high-low range vs its value N periods ago -- when it has
been low for a prolonged period and then starts rising, it signals an
impending price move (breakout out of consolidation). The source's own
"Trading Strategy" and "with Moving Averages and RSI" sections give a
concrete composite rule: buy when (1) Chaikin Volatility is rising off a
low base, (2) price is above its 50-day SMA (uptrend), and (3) RSI(14) is
above 50 (bullish momentum confirmation); exit when Chaikin Volatility
starts declining (trend losing momentum) and RSI drops back below 50.
First Chaikin-Volatility entry in this repo (0 prior KB hits) -- distinct
from ATR-based volatility filters used elsewhere (Chaikin Volatility
explicitly ignores gaps, using only the HL range's EMA rate-of-change,
rather than ATR's true-range/gap-inclusive measure) and from every
existing RSI-threshold strategy here (this uses RSI purely as a >50/<50
regime confirmation gate alongside an independent volatility-expansion
trigger, not as an oversold/overbought entry signal itself).

Signal logic (long side only)
------------------------------
- Chaikin Volatility (CV): EMA(high-low, cv_ema_period), then CV_t =
  100 * (ema_t - ema_{t-cv_lookback}) / ema_{t-cv_lookback}.
- "Rising off a low base": CV crosses above `cv_rise_threshold` (e.g. 0.0,
  i.e. turns positive) having been below it in the prior bar.
- Entry: CV rising-crossover AND close > SMA(trend_window) AND
  RSI(rsi_period) > rsi_bull_threshold (default 50).
- Exit: RSI falls back below rsi_bull_threshold, OR CV turns negative
  (volatility contracting again -- trend losing momentum), OR
  `max_hold_days` time-stop.

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
    cv_ema_period: int = 10,
    cv_lookback: int = 10,
    cv_rise_threshold: float = 0.0,
    trend_window: int = 50,
    rsi_period: int = 14,
    rsi_bull_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(df)

    hl_range = high - low
    ema_range = hl_range.ewm(span=cv_ema_period, adjust=False, min_periods=cv_ema_period).mean()
    ema_range_lagged = ema_range.shift(cv_lookback)
    cv = 100 * (ema_range - ema_range_lagged) / ema_range_lagged.replace(0, float("nan"))

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    rsi = _rsi(close, rsi_period)

    cv_rising_cross = (cv > cv_rise_threshold) & (cv.shift(1) <= cv_rise_threshold)
    cv_rising_cross = cv_rising_cross.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_cond = (rsi.iloc[i] < rsi_bull_threshold) or (cv.iloc[i] < 0) or (held >= max_hold_days)
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(cv_rising_cross.iloc[i]) and bool(uptrend.iloc[i]) and rsi.iloc[i] > rsi_bull_threshold:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` scales position size by a fixed multiplier (repo's
    established leverage-cap-recalibration rescue pattern) -- default 1.0
    preserves prior behavior exactly.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
