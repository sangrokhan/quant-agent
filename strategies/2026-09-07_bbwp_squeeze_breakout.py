"""Strategy: Bollinger Band Width Percentile (BBWP) squeeze breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-003):
Bollinger Band Width (BBW = (upper-lower)/basis) measures current
volatility. Ranking today's BBW as a percentile against its own trailing
lookback (BBWP, per TradingView's "Bollinger Band Width Percentile"
convention) identifies genuinely historically-narrow volatility regimes
("squeeze") rather than an arbitrary fixed BBW threshold, which would not
adapt across different assets/regimes. Per the source's own rule (a
TradingView Pine Script, kr.tradingview.com/scripts/bollingerbandstrategy):
BBWP<=25% = squeeze (bands historically narrow), BBWP<15% = "tight
squeeze" (higher-probability setup). Trading rule: wait for a squeeze, then
enter LONG in the breakout direction once price closes outside the upper
Bollinger Band (source explicitly frames squeeze-breakout as the
"highest probability setup", direction-agnostic in the source but we only
trade the long/upside breakout per this repo's long-only convention).

First strategy in this repo using a PERCENTILE-RANKED (not raw/fixed-
threshold) Bollinger Band Width squeeze signal -- distinct from
2026-09-05-023's raw BB bandwidth squeeze breakout (rejected, but with a
non-percentile threshold) since normalizing to a percentile rank should be
more robust across different vol regimes/assets than a fixed absolute
bandwidth cutoff.

Signal logic
------------
- Bollinger Bands: basis = SMA(bb_window), upper/lower = basis +/- bb_std*std.
- BBW_t = (upper_t - lower_t) / basis_t.
- BBWP_t = percentile rank of BBW_t within the trailing bbwp_lookback-bar
  window (0-100 scale; source's own convention).
- Squeeze flag: BBWP_t <= squeeze_pct (default 25, per source).
- Entry (long): squeeze was true on the PRIOR bar (bands were compressed)
  AND today's close breaks above today's upper Bollinger Band (breakout
  confirmation) -- captures "squeeze -> breakout" rather than requiring the
  squeeze condition to still hold exactly on the breakout bar itself (bands
  naturally widen the moment the breakout occurs).
- Exit: close crosses back below the basis (SMA) line, OR after
  max_hold_days trading days.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    bbwp_lookback: int = 100,
    squeeze_pct: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = sma + bb_std * std
    lower = sma - bb_std * std
    bbw = (upper - lower) / sma

    bbwp = bbw.rolling(bbwp_lookback).apply(
        lambda w: (w[:-1] <= w[-1]).mean() * 100.0 if len(w) > 1 else float("nan"),
        raw=True,
    )

    squeeze = (bbwp <= squeeze_pct).fillna(False)
    squeeze_prev = squeeze.shift(1).fillna(False)
    breakout = close > upper

    entry = squeeze_prev & breakout
    exit_meanrev = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
