"""Strategy: Bollinger Band squeeze breakout (long-only), gated on a
volatility-contraction ("squeeze") precondition before the breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-011):
Source: http://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/
-- the classic squeeze-breakout idea: Bollinger Band width (upper minus
lower band) contracting to an unusually low value signals a volatility
consolidation ("squeeze"); a subsequent breakout beyond the bands is
expected to continue in that direction. The source's own extensive
backtesting (many assets/parameter variants) found this does NOT beat
buy-and-hold on nearly any asset tested -- an explicit documented negative
prior. This iteration tests it on this repo's universe mainly to
confirm/falsify that finding here, using a standard construction (bandwidth
at a rolling percentile low + close breaking above the upper band) since the
source's exact numeric rule table wasn't available in the extracted content.

This is distinct from every prior strategy in this log: 2026-09-03-001 (BB
mean-reversion) trades AGAINST the bands (fade back to the mean) with an
unconditional entry; this trades WITH a breakout beyond the bands, but only
when preceded by a volatility squeeze (band-width percentile filter) --
structurally a breakout/continuation bet, not a mean-reversion bet, and
conditioned on a *squeeze precondition* that 2026-09-03-008's Donchian
breakout (a pure price-channel breakout, no volatility-contraction gate)
does not use.

Signal logic
------------
- Bollinger Bands: `bb_window`-day SMA +/- `bb_std` standard deviations.
- Band width = upper_band - lower_band, normalized by the SMA (relative
  width) for comparability across price levels.
- Squeeze flag: today's relative band width is at or below the
  `squeeze_percentile` percentile of its trailing `squeeze_lookback`-day
  history (a genuine volatility contraction, not just "narrow" in absolute
  terms).
- Entry (long): close crosses above the upper band AND a squeeze was active
  within the prior `squeeze_recency` days (breakout emerging from a recent
  consolidation, not a breakout with no preceding contraction).
- Exit: close crosses back below the `bb_window`-day SMA (trend exhausted),
  or after `max_hold_days` trading days (avoid indefinite holds).
- Flat otherwise; long-only, no shorts.

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


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    squeeze_lookback: int = 120,
    squeeze_percentile: float = 0.20,
    squeeze_recency: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper_band = sma + bb_std * std
    lower_band = sma - bb_std * std
    rel_width = (upper_band - lower_band) / sma

    width_pctile_threshold = rel_width.rolling(squeeze_lookback).quantile(squeeze_percentile)
    is_squeeze = rel_width <= width_pctile_threshold
    squeeze_recent = is_squeeze.rolling(squeeze_recency, min_periods=1).max().astype(bool)

    breakout = close > upper_band
    entry = breakout & squeeze_recent.fillna(False)
    exit_trend = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend.iloc[i]) or held >= max_hold_days:
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
