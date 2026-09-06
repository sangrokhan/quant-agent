"""Strategy: ATR-Percentile volatility-regime trend filter, long-only.

Hypothesis (see knowledge_base id 2026-09-06-163):
Per QuantifiedStrategies.com's "ATR Percentile-Based Grid Trading for
Crypto Markets" article (surfaced via Google search snippet -- the article
URL itself now 404s, so the specific threshold rule was taken from the
Google search-result snippet directly): a volatility regime can be
classified via ATR Percentile (ATR's percentile RANK within its own
trailing lookback distribution, not raw ATR level): High volatility when
ATR Percentile >= 70-80, Low volatility when ATR Percentile <= 25-30,
Neutral in between (30-70).

The source's own strategy is multi-level GRID trading (place a ladder of
limit buy/sell orders spaced by an ATR-derived interval, activated more
aggressively in the high-vol regime) -- that order-ladder mechanism doesn't
map onto this repo's single 0/1-position `generate_signals` contract
(no grid/ladder execution model here), so this repo adapts only the core
ATR-PERCENTILE REGIME-CLASSIFICATION rule, combined with a simple trend
filter: trade a plain trend-following long ONLY during the NEUTRAL
volatility band (ATR percentile between `low_threshold` and
`high_threshold`) -- avoiding both the low-vol "nothing happening" regime
(no real trend to catch) and the high-vol "chaotic/gap-risk" regime (the
source's own rationale for scaling grid activity differently in each band,
reinterpreted here as "avoid directional bets when volatility is at either
extreme").

Signal logic
------------
- ATR (14-period, standard Wilder-style true-range average).
- ATR Percentile: `atr_pctile_window`-day rolling percentile RANK of
  today's ATR value within its own trailing distribution (0-100 scale,
  matching the source's own "ATR Percentile" terminology).
- Neutral vol regime: `low_threshold` <= ATR percentile <= `high_threshold`.
- Trend signal: close > SMA(`trend_window`).
- Entry (long): trend signal AND neutral vol regime.
- Exit: trend signal breaks (close < SMA) OR vol regime exits the neutral
  band (either direction) OR a `max_hold_days` time-stop.

First ATR-Percentile-as-regime-classifier strategy in this repo -- distinct
from HVR ratio (2026-09-06-109, a two-horizon std-dev RATIO, not a
percentile RANK) and every other single-horizon range/ATR measure (ATR
Expansion Breakout, Bollinger Bandwidth Squeeze, Choppiness Index, VHF,
Random Walk Index) since this one gates on a NEUTRAL middle band rather
than an expansion/contraction threshold crossing.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    atr_pctile_window: int = 100,
    low_threshold: float = 30.0,
    high_threshold: float = 70.0,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    atr = _atr(df, atr_window)
    atr_pctile = atr.rolling(atr_pctile_window, min_periods=atr_window).rank(pct=True) * 100.0

    neutral_vol = (atr_pctile >= low_threshold) & (atr_pctile <= high_threshold)

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    entry = uptrend.fillna(False) & neutral_vol.fillna(False)
    exit_signal = (~uptrend.fillna(False)) | (~neutral_vol.fillna(False))

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
