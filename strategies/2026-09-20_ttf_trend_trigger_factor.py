"""Strategy: Trend Trigger Factor (TTF, M.H. Pee) threshold-cross trend system.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-117):
Per Tokenist's TTF explainer (https://www.tokenist.com/trading-indicators/trend-trigger-factor-indicator/),
M.H. Pee's Trend Trigger Factor measures trend direction/strength via two
non-overlapping N-day lookback windows:
    Buy Power  = HighestHigh(days 1..N)   - LowestLow(days N+1..2N)
    Sell Power = HighestHigh(days N+1..2N) - LowestLow(days 1..N)
    TTF = [(Buy Power - Sell Power) / (0.5 * (Buy Power + Sell Power))] * 100
The creator's own disclosed rule: TTF > +100 signals a bull trend (go/stay
long); TTF < -100 signals a bear trend (go/stay short); values between the
two thresholds mean "hold your current position" (the full system is
always-in-the-market with reversals). First TTF strategy in this repo (0
prior matches for "Trend Trigger Factor"/"TTF").

This repo's standard convention is long-only (0/1 position), so we adapt
the source's reversal system to a long/flat hysteresis state machine: go
long when TTF crosses above the upper threshold (+100 default), go flat
when TTF crosses below the lower threshold (-100 default, i.e. treat the
source's "go short" trigger as "exit to flat" instead), hold the current
state while TTF is between the two thresholds (matching the source's own
"maintain your current position" rule in that zone).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ttf(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Compute M.H. Pee's Trend Trigger Factor over a rolling window."""
    n = window
    hh_recent = high.rolling(n).max()
    ll_recent = low.rolling(n).min()
    hh_prior = high.shift(n).rolling(n).max()
    ll_prior = low.shift(n).rolling(n).min()

    buy_power = hh_recent - ll_prior
    sell_power = hh_prior - ll_recent

    denom = 0.5 * (buy_power + sell_power)
    ttf = (buy_power - sell_power) / denom.replace(0, pd.NA) * 100.0
    return ttf.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    ttf_window: int = 15,
    upper_threshold: float = 100.0,
    lower_threshold: float = -100.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]

    ttf = _ttf(high, low, ttf_window)

    position = pd.Series(0, index=high.index, dtype=int)
    state = 0  # 0 = flat, 1 = long
    for i in range(len(high)):
        val = ttf.iloc[i]
        if pd.isna(val):
            position.iloc[i] = state
            continue
        if val > upper_threshold:
            state = 1
        elif val < lower_threshold:
            state = 0
        # else: hold current state (hysteresis zone)
        position.iloc[i] = state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
