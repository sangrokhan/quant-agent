"""Strategy: Consecutive-Down-Week ATR-Magnitude Mean Reversion (weekly bars).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per StatOasis's "Weekly Mean Reversion Strategy: 22,680 Backtests Say the
Rule Works and the Volume Filter Does Not"
(https://statoasis.com/overfit/research/a-simple-weekly-mean-reversion-strategy-for-index-futures,
Ali Casey, visited this iteration via browser_exec -- web_search DDGS
backend errored/empty on multiple queries this iteration), the plain
single-down-week buy rule (already accepted in this repo,
strategies/2026-09-20_sp500_down_week_reversion.py, id 2026-09-19-064)
is only ONE cell of the source's much larger 22,680-variant grid. The
source explicitly varied six dimensions the repo's existing accepted
strategy does NOT test: direction, hold length (1-21 weeks), number of
CONSECUTIVE down weeks required (1, 2, or 3), and drop magnitude measured
in units of 20-week ATR (not a simple percentage). This strategy tests
the genuinely distinct combination the source flagged as producing a
materially different risk profile at longer holds ("Holding 21 weeks
instead of 1 lifted the ES win rate from 58.1% to 75.6%"): requiring
consecutive_down_weeks (default 2) of decline, each week's drop measured
against a 20-week ATR floor (atr_mult), before entering, then holding for
hold_weeks (default multi-week, not the accepted strategy's fixed 1-week
hold) rather than exiting on the very next weekly close. This is a
distinct construction from 2026-09-19-064 (single down week, percentage
magnitude, fixed 1-week hold) — testing whether requiring a DEEPER,
multi-week-confirmed decline and holding LONGER captures a more durable
edge, per the source's own finding that risk-adjusted metrics (return/DD)
diverge meaningfully by hold length and market.

Signal logic (converted to a daily-bar approximation of the source's
weekly-bar construction, since this repo's data/loaders.py provides daily
OHLCV, not native weekly bars -- weekly bars are resampled internally from
daily closes, Friday-anchored):
- Resample daily close to weekly (W-FRI) bars.
- A "down week" = this week's close < previous week's close.
- entry_signal = True when the last `consecutive_down_weeks` weeks were ALL
  down weeks AND the cumulative decline over that window exceeds
  atr_mult * ATR(20 weeks) (ATR computed on the weekly-resampled OHLC).
- On an entry week's Friday close, go long; hold for exactly `hold_weeks`
  weeks, then exit at that week's Friday close (source's own "sell that
  week's close" framing generalized to N weeks).
- Position is projected back onto the daily index (held flat/long across
  the intervening daily bars) for validator/grid compatibility with this
  repo's daily-bar pipeline.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 daily position)
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


def _weekly_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    weekly = df.resample("W-FRI").agg({
        "open": "first", "high": "max", "low": "min", "close": "last",
    }).dropna()
    return weekly


def _weekly_atr(weekly: pd.DataFrame, window: int = 20) -> pd.Series:
    high = weekly["high"]
    low = weekly["low"]
    prev_close = weekly["close"].shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def _weekly_position(weekly: pd.DataFrame, consecutive_down_weeks: int, atr_mult: float,
                      hold_weeks: int, atr_window: int) -> pd.Series:
    close = weekly["close"]
    is_down = (close < close.shift(1)).fillna(False)

    down_streak = pd.Series(True, index=close.index)
    for lag in range(consecutive_down_weeks):
        down_streak &= is_down.shift(lag).fillna(False)

    atr = _weekly_atr(weekly, atr_window)
    decline_magnitude = (close.shift(consecutive_down_weeks) - close)
    magnitude_ok = (decline_magnitude >= atr_mult * atr).fillna(False)

    entry = (down_streak & magnitude_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    hold_remaining = 0
    for i in range(len(close)):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
        elif bool(entry.iloc[i]):
            position.iloc[i] = 1
            hold_remaining = hold_weeks - 1
    return position


def generate_signals(
    price_df: pd.DataFrame,
    consecutive_down_weeks: int = 2,
    atr_mult: float = 0.5,
    hold_weeks: int = 3,
    atr_window: int = 20,
) -> pd.Series:
    """Return a {0,1} daily long/flat position series (weekly-decision, daily-projected)."""
    df = _prep(price_df)
    weekly = _weekly_ohlc(df)
    weekly_pos = _weekly_position(weekly, consecutive_down_weeks, atr_mult, hold_weeks, atr_window)

    # Project weekly position forward onto the daily index: each daily bar
    # inherits the position decided as of the most recently completed
    # weekly bar (no look-ahead -- reindex with ffill against weekly index
    # dates, which mark each week's Friday close).
    daily_pos = weekly_pos.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_pos


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
