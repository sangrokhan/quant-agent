"""Strategy: Chaikin Volatility zero-line-cross "expansion" signal, gated by
an SMA uptrend filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-079):
Per Definedge Securities' Chaikin Volatility documentation (surfaced via
Google search snippet, browser_exec fallback since web_search DDGS returned
connection errors this iteration): "Expansion: Chaikin Volatility crosses
above zero after staying below it. Contraction: Chaikin Volatility crosses
below zero after staying above it." This is a distinct zero-line-cross
construction from the already-rejected trough-reversal-from-rolling-extreme
Chaikin Volatility variant tested in this repo (2026-09-04-133, which
entered on CV rising off a trailing low rather than a raw zero-line cross).
Chaikin Volatility itself carries no directional signal (it just measures
whether the high-low range is expanding or contracting), so gated here by
an SMA uptrend filter: only take the volatility-expansion signal as
confirmation of a fresh directional move when already in an established
uptrend.

CV formula (standard Marc Chaikin):
    ema_range = EMA(High - Low, ema_period)
    CV = 100 * (ema_range - ema_range.shift(roc_period)) / ema_range.shift(roc_period)

Signal logic
------------
- Chaikin Volatility (CV) crosses from <=0 to >0 (expansion signal) AND
  close > SMA(trend_window) (uptrend confirmation) => long entry.
- Exit: CV crosses back below 0 (contraction, volatility drying up), OR
  close crosses below SMA(trend_window) (trend filter breaks), OR a
  max_hold_days time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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
    ema_range = hl_range.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    shifted = ema_range.shift(roc_period)
    cv = 100.0 * (ema_range - shifted) / shifted.replace(0, pd.NA)
    return cv


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 10,
    roc_period: int = 10,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cv = _chaikin_volatility(df, ema_period, roc_period)
    sma = close.rolling(trend_window).mean()

    prev_cv = cv.shift(1)
    expansion_cross = (cv > 0) & (prev_cv <= 0)
    contraction_cross = (cv < 0) & (prev_cv >= 0)
    uptrend = close > sma

    entry = expansion_cross & uptrend.fillna(False)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(contraction_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
