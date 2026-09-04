"""Strategy: Connors RSI (CRSI) mean-reversion extreme-threshold entry/exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-113):
Larry Connors' composite RSI (CRSI) averages three sub-indicators to build a
faster, more responsive short-term oscillator than the classic 14-day RSI:
  1. RSI(rsi_period) of the closing price (standard Wilder RSI, short period).
  2. RSI(streak_period) of the "up/down streak" length (a running count of
     consecutive up-closes, positive, or down-closes, negative, resets to 0
     on a flat/unchanged close) -- captures trend persistence/duration.
  3. PercentRank(pctrank_period) of today's 1-day rate-of-change -- captures
     the *magnitude* of today's move relative to the recent history.
CRSI = mean(RSI_price, RSI_streak, PercentRank_ROC), textbook parameters
CRSI(3, 2, 100).

Per https://www.quantifiedstrategies.com/connors-rsi/: because CRSI moves
much faster than a 14-day RSI, overbought/oversold bands are set far wider
(~90 overbought / ~10 oversold) than the classic 70/30. Source's own SPY
backtest: "buy when CRSI < 15, sell when CRSI > 85" produced the best
profit factor (~2.08 over 288 trades). Implemented here long-only: entry
on CRSI closing below entry_threshold, exit on CRSI closing back above
exit_threshold (or after max_hold_days as a safety time-stop, since the
source's own worked simple-exit example -- "close > yesterday's high" --
performed poorly and CRSI-band-based exits are the article's headline
approach).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _updown_streak(close: pd.Series) -> pd.Series:
    """Running streak length: +N for N consecutive up-closes, -N for N
    consecutive down-closes, 0 on an unchanged close (resets)."""
    delta = close.diff()
    direction = np.sign(delta).fillna(0.0)
    streak = np.zeros(len(close))
    for i in range(1, len(close)):
        d = direction.iloc[i]
        if d == 0:
            streak[i] = 0.0
        elif d > 0:
            streak[i] = streak[i - 1] + 1 if streak[i - 1] >= 0 else 1
        else:
            streak[i] = streak[i - 1] - 1 if streak[i - 1] <= 0 else -1
    return pd.Series(streak, index=close.index)


def _percent_rank(series: pd.Series, period: int) -> pd.Series:
    def _rank(window: np.ndarray) -> float:
        last = window[-1]
        return 100.0 * (np.sum(window[:-1] <= last) / (len(window) - 1)) if len(window) > 1 else 50.0

    return series.rolling(period + 1).apply(_rank, raw=True)


def _connors_rsi(
    close: pd.Series, rsi_period: int, streak_period: int, pctrank_period: int
) -> pd.Series:
    rsi_price = _wilder_rsi(close, rsi_period)
    streak = _updown_streak(close)
    rsi_streak = _wilder_rsi(streak, streak_period)
    roc1 = close.pct_change(1) * 100.0
    pct_rank = _percent_rank(roc1, pctrank_period)
    crsi = (rsi_price + rsi_streak + pct_rank) / 3.0
    return crsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    streak_period: int = 2,
    pctrank_period: int = 100,
    entry_threshold: float = 15.0,
    exit_threshold: float = 85.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    crsi = _connors_rsi(close, rsi_period, streak_period, pctrank_period)
    valid = crsi.notna()

    entry = (crsi < entry_threshold) & valid
    exit_signal = (crsi > exit_threshold) & valid

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if exit_signal.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    streak_period: int = 2,
    pctrank_period: int = 100,
    entry_threshold: float = 15.0,
    exit_threshold: float = 85.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns: yesterday's position times today's close-close return."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        rsi_period=rsi_period,
        streak_period=streak_period,
        pctrank_period=pctrank_period,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )
    price_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * price_returns
    return strat_returns.fillna(0.0)
