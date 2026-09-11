"""Strategy: Weekly RSI(2) mean reversion (XLP-style, low-turnover).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-077):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/quantitative-trading-strategies/,
visited this iteration): on WEEKLY bars, "when the 2-week RSI crosses
below 15, we go long at Friday's close. We sell when the 2-weekly RSI
crosses above 20." Source's own XLP backtest: average gain per trade
1.2%, annual return 4.2% at only 11% time invested (source notes
risk-adjusted return of ~37% when normalized by time invested).

This is the first WEEKLY-bar (not daily) RSI mean-reversion strategy in
this repo -- distinct from every prior daily-bar RSI2/RSI4/RSI14 variant.
The weekly-bar construction is inherently much lower-turnover than a
comparable daily-bar oscillator strategy (a structural fit for this cron
trigger's repeated transaction-cost-driven rejections of high-frequency
daily mean-reversion ideas: 2026-09-11-072, -074, -076).

Signal logic
------------
- Resample price_df to weekly (Friday-close) bars.
- Compute a classic Wilder RSI(2) on the weekly close series.
- Long entry: weekly RSI(2) crosses BELOW 15 (source's rule: "crosses
  below" -- i.e. was >=15 last week, is <15 this week).
- Exit: weekly RSI(2) crosses ABOVE 20 (was <=20 last week, is >20 this
  week).
- Forward-fill the resulting weekly position onto the daily index (no
  look-ahead: a Friday-close-derived decision only takes effect on
  Monday and thereafter until the next weekly signal).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weekly_close(df: pd.DataFrame) -> pd.Series:
    idx = pd.to_datetime(df.index).tz_localize(None)
    close = df["close"].copy()
    close.index = idx
    return close.resample("W-FRI").last().dropna()


def _wilder_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss > 0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    entry_threshold: float = 15.0,
    exit_threshold: float = 20.0,
) -> pd.Series:
    """Return a daily {0,1} long/flat position series, driven by a weekly
    RSI(2) crossunder/crossover, forward-filled onto the daily index."""
    df = _prep(price_df)
    weekly_close = _weekly_close(df)
    weekly_rsi = _wilder_rsi(weekly_close, rsi_period)

    entry_cross = (weekly_rsi < entry_threshold) & (weekly_rsi.shift(1) >= entry_threshold)
    exit_cross = (weekly_rsi > exit_threshold) & (weekly_rsi.shift(1) <= exit_threshold)

    weekly_pos = pd.Series(0, index=weekly_rsi.index, dtype=int)
    in_position = False
    for i in range(len(weekly_rsi)):
        if in_position:
            if bool(exit_cross.iloc[i]):
                in_position = False
                weekly_pos.iloc[i] = 0
            else:
                weekly_pos.iloc[i] = 1
        else:
            if bool(entry_cross.iloc[i]):
                in_position = True
                weekly_pos.iloc[i] = 1
            else:
                weekly_pos.iloc[i] = 0

    daily_index = pd.to_datetime(df.index).tz_localize(None)
    # Position decided at Friday close takes effect starting the FOLLOWING
    # trading day (Monday) -- shift by one week-bar before reindexing.
    weekly_pos_shifted = weekly_pos.shift(1).fillna(0).astype(int)

    daily_pos = weekly_pos_shifted.reindex(daily_index, method="ffill")
    daily_pos = daily_pos.fillna(0).astype(int)
    daily_pos.index = df.index
    return daily_pos


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
