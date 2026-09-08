"""Strategy: Larry Connors' Cumulative RSI(2) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-134):
Per https://www.quantitativo.com/p/squeezing-more-profits-with-cumulative
(Quantitativo's own re-verification of Larry Connors' "Short Term Trading
Strategies That Work" Cumulative RSI concept): sum the past `cum_days`
daily readings of a 2-period RSI into a single "Cumulative RSI" value; buy
when Cumulative RSI is below `entry_threshold`; exit when the (single-day,
non-cumulative) 2-period RSI closes above `exit_threshold`; gated by a
200-day SMA uptrend filter. Per Connors' own quote (via the source):
"positive, healthy returns in U.S. indices, in ETFs, on world indices...".
The source's own statistical test found cumulative-RSI events produce
meaningfully better expected returns (1.0% vs 0.6%) and payoff ratio (0.84
vs 0.50) than the vanilla single-day RSI(2) threshold already accepted in
this repo (2026-09-03-005).

This is DISTINCT from every other RSI(2)-family strategy already in this
repo: it sums (accumulates) RSI readings across a rolling window into one
value compared against a threshold, rather than checking a single day's
RSI value (2026-09-03-005), a multi-day monotonic decline (R3, 2026-09-08-
087/2026-09-06-159), or N-consecutive-days-all-below-threshold persistence
(2026-09-08-089) -- the summed magnitude captures both HOW oversold and
HOW LONG, in one number, which is Connors' own stated rationale for it
being a "better variation."

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    cum_days: int = 2,
    entry_threshold: float = 10.0,
    exit_threshold: float = 65.0,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi2 = _rsi(close, rsi_period)
    cumulative_rsi = rsi2.rolling(cum_days).sum()
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (cumulative_rsi < entry_threshold) & uptrend.fillna(False)
    exit_signal = rsi2 > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]) or not bool(uptrend.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
