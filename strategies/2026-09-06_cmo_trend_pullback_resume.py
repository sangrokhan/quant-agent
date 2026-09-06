"""Strategy: Chande Momentum Oscillator (CMO) trend-pullback resumption.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per TradingSim's CMO guide (https://www.tradingsim.com/blog/chande-momentum-oscillator-cmo-technical-indicator),
the CMO works best "as a confirmation layer rather than a standalone
trigger": in an established uptrend, wait for the CMO to pull back toward
zero (or into mildly negative territory) and then turn back up, signaling
that momentum is resuming WITH the prevailing trend -- rather than trading
a fixed +-50 overbought/oversold threshold cross (already tested and
rejected in this repo, 2026-09-04-055) or a CMO/signal-line crossover
(already tested and rejected, 2026-09-05-064). This is the first
"trend-filtered pullback-and-turn" CMO variant in this repo.

Signal logic
------------
- Trend filter: close > SMA(trend_window) (established uptrend).
- CMO(cmo_period) = 100 * (Su - Sd) / (Su + Sd), where Su/Sd are the sums
  of up-day / down-day |close diffs| over the lookback.
- Pullback trigger: CMO dips to <= pullback_threshold (default 0.0, i.e.
  "toward zero or mildly negative") at some point within the trailing
  pullback_lookback bars, and CMO today > CMO yesterday (turning back up),
  while the trend filter is bullish today.
- Exit: CMO crosses back above overbought_threshold (default 50, source's
  own overbought reference level), OR trend filter breaks (close <=
  SMA(trend_window)), OR a max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cmo(close: pd.Series, cmo_period: int) -> pd.Series:
    diff = close.diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    su = up.rolling(cmo_period).sum()
    sd = down.rolling(cmo_period).sum()
    denom = (su + sd).replace(0.0, pd.NA)
    cmo = 100.0 * (su - sd) / denom
    return cmo


def generate_signals(
    price_df: pd.DataFrame,
    cmo_period: int = 14,
    trend_window: int = 50,
    pullback_threshold: float = 0.0,
    pullback_lookback: int = 5,
    overbought_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cmo = _cmo(close, cmo_period)
    prev_cmo = cmo.shift(1)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    # Was CMO <= pullback_threshold at any point in the trailing window
    # (including today), then turning up today.
    dipped_recently = (cmo <= pullback_threshold).rolling(pullback_lookback).max().fillna(0).astype(bool)
    turning_up = cmo > prev_cmo

    entry = uptrend & dipped_recently & turning_up
    entry = entry.fillna(False)

    exit_overbought = cmo >= overbought_threshold
    trend_break = ~uptrend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            do_exit = bool(exit_overbought.iloc[i]) or bool(trend_break.iloc[i]) or held >= max_hold_days
            if do_exit:
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
