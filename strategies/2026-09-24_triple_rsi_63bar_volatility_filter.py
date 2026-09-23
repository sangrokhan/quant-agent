"""Strategy: Triple RSI (Connors/QuantifiedStrategies canonical rule) WITH
the "RSI below its value N bars ago" volatility/freshness filter that
StatOasis's "Better-RSI Showdown" (Sep 2026, Ali Casey) explicitly identified
as the missing ingredient in every prior naive reproduction attempt.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://statoasis.com/overfit/research/better-rsi-backtest (visited this
iteration via browser_exec -- web_search DDGS backend errored/empty on
multiple queries this iteration), a 1,856-backtest study on SPY/QQQ/IWM/DIA
found that a straightforward 3-condition Triple RSI implementation:
    (1) RSI(n) < 30 (oversold)
    (2) RSI(n) has declined for 3 consecutive bars
    (3) close > SMA(200) (long-term uptrend filter)
reproduces only a 58.9%-65.1% win rate on SPY, NOT the ~90% headline claim
attributed to QuantifiedStrategies. The article's own diagnosis: "the
canonical version includes a 'RSI below its 63-bar-ago value' condition
that the tested implementation omits, so the tested rule lets through
trades the canonical version would skip... What the filter would do to the
win rate was never measured [in that study]." This repo's own prior Triple
RSI entry (2026-09-09-050) also tested the single-RSI streak-decline
variant but used a DIFFERENT freshness filter ("RSI was above 60 three
days ago", not "RSI below its own 63-bar-ago value") -- so the specific
condition StatOasis flags as the reproduction gap has never actually been
tested in this repo. This iteration adds EXACTLY that missing filter (a
long-horizon RSI-momentum-decay confirmation: today's RSI must be below
where RSI stood roughly one calendar quarter -- 63 trading bars -- ago,
confirming a structural rather than one-off oversold dip) to the identical
3-condition base rule, to directly test whether it is the ingredient that
recovers the higher win rate / better risk-adjusted profile the study
couldn't measure.

Signal logic
------------
- rsi = Wilder RSI(rsi_window) of close (default rsi_window=5, matching the
  QuantifiedStrategies canonical variant per the source article).
- Entry (long): at today's close,
    (1) rsi < oversold_threshold (default 30)
    (2) rsi has been strictly declining for streak_days consecutive bars
        (rsi[t] < rsi[t-1] < ... < rsi[t-streak_days])
    (3) close > SMA(trend_window) (default 200, long-term uptrend filter)
    (4) rsi < rsi.shift(lookback_bars) (the StatOasis-flagged missing
        filter: today's RSI reading is below its own value ~1 quarter ago,
        i.e. this dip is deeper than the recent-quarter norm, not just a
        3-day wiggle around an already-elevated baseline)
- Exit: rsi recovers above exit_threshold (default 55), OR a
  max_hold_days time-stop (default matches the source's tested 10-bar
  hold, the best-performing hold length in the study's own head-to-head).
- Flat otherwise.

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
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _declining_streak(rsi: pd.Series, streak_days: int) -> pd.Series:
    """True where rsi[t] < rsi[t-1] < ... < rsi[t-streak_days] (strict decline)."""
    diffs = rsi.diff()
    is_down = diffs < 0
    result = pd.Series(True, index=rsi.index)
    for lag in range(streak_days):
        result &= is_down.shift(lag).fillna(False)
    return result


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 5,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 55.0,
    streak_days: int = 3,
    trend_window: int = 200,
    lookback_bars: int = 63,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _wilder_rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()

    oversold = rsi < oversold_threshold
    declining = _declining_streak(rsi, streak_days)
    uptrend = close > sma_trend
    rsi_below_quarter_ago = rsi < rsi.shift(lookback_bars)

    entry = (oversold & declining & uptrend & rsi_below_quarter_ago).fillna(False)
    exit_signal = (rsi > exit_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
