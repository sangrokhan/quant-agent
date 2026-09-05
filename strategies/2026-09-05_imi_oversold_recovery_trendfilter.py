"""Strategy: Intraday Momentum Index (IMI, Tushar Chande) oversold-recovery
signal-cross, gated by an uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-071):
The Intraday Momentum Index (Tushar Chande) is an RSI-analog computed from
each bar's own open-to-close move (sum of up-days' (close-open) gains over
sum of up-days' gains plus down-days' (open-close) losses, over an
imi_window lookback) rather than close-to-close changes -- capturing
intraday buying/selling pressure rather than day-over-day momentum. Per a
GoCharting IMI day-trading-strategy article (search-result snippet):
"Enter long when IMI drops below 30 and then crosses back above 30 during
an established intraday uptrend. Use the 14-period default." Operationalized
here on daily OHLC bars (source's own EOD-adaptable framing) with the
"established uptrend" gate implemented as close > SMA(trend_window),
matching this repo's standard convention for oscillator-uptrend-gate
strategies (e.g. CCI/RSI-family entries). First IMI-family strategy in this
repo -- distinct from mechanically-related Relative Momentum Index (RMI,
2026-09-05-013, momentum-lookback RSI variant on close-to-close changes)
and Money Flow Index (MFI, 2026-09-04-033/2026-09-05-011/061, volume-weighted
RSI variant) -- IMI is the only one of the three keyed on each bar's own
open-vs-close intrabar direction rather than bar-to-bar close changes or
volume.

Signal logic
------------
- IMI(imi_window) = 100 * sum(up_days' (close-open)) /
  (sum(up_days' (close-open)) + sum(down_days' (open-close))), over a
  rolling imi_window lookback (0-100 scale).
- Entry (long): IMI was below oversold_threshold (default 30) within the
  last recovery_lookback bars, AND IMI has now crossed back above
  oversold_threshold, AND close > SMA(trend_window) (uptrend gate).
- Exit: IMI crosses above overbought_threshold (default 70, take-profit
  extreme) OR back below oversold_threshold (failed bounce) OR the trend
  filter breaks OR a max_hold_days time-stop.

Interface contract (RESEARCH_LOOP.md Step 5):
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


def _imi(open_: pd.Series, close: pd.Series, window: int) -> pd.Series:
    up_gain = (close - open_).clip(lower=0.0)
    down_loss = (open_ - close).clip(lower=0.0)
    sum_up = up_gain.rolling(window).sum()
    sum_down = down_loss.rolling(window).sum()
    denom = sum_up + sum_down
    imi = 100.0 * sum_up / denom.replace(0.0, pd.NA)
    return imi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    imi_window: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    recovery_lookback: int = 3,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    imi = _imi(open_, close, imi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    was_oversold_recently = (
        (imi < oversold_threshold).rolling(recovery_lookback).max().fillna(0).astype(bool)
    )
    cross_back_above = (imi >= oversold_threshold) & (imi.shift(1) < oversold_threshold)
    entry = was_oversold_recently.shift(1).fillna(False) & cross_back_above.fillna(False) & uptrend.fillna(False)

    exit_overbought = (imi >= overbought_threshold) & (imi.shift(1) < overbought_threshold)
    exit_failed_bounce = imi < oversold_threshold
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_overbought.iloc[i])
                or bool(exit_failed_bounce.iloc[i])
                or bool(exit_trend_break.iloc[i])
                or held >= max_hold_days
            ):
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
