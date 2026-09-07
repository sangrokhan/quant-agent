"""Strategy: HV-rank compression gate + Donchian breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-118):
Per https://www.luxalgo.com/library/concept/volatility-percentile-rank/,
normalizing a volatility measure (here: 20-day close-to-close realized
volatility) against its own trailing 252-day distribution onto a 0-100
percentile scale identifies compression (low percentile) vs stress (high
percentile) regimes better than an absolute volatility threshold, because
"a 2% daily range is sleepy for one instrument and violent for another, so
absolute numbers do not travel." The source's stated standard usage pattern
is: "breakout systems often require a low volatility percentile
(compression) before arming entries." This strategy operationalizes that
directly: only take a Donchian-channel breakout (close > rolling N-day
high) when the 20-day realized-vol percentile (over the trailing 252 days)
is below a low threshold (compression), exit on close < rolling N-day low
or a max-holding-period time-stop. This is a CONTINUOUS percentile gate,
distinct from the already-tested binary TTM Squeeze (Bollinger-inside-
Keltner squeeze detection, 2026-09-04-091/2026-09-04-126, both rejected) --
first HV-rank/percentile-gated strategy in this repo.

Signal logic
------------
- 20-day realized vol (std of daily log returns, annualized).
- hv_percentile: for each bar, the percentile rank of today's realized vol
  within the trailing `percentile_window` (default 252) days (0=quietest,
  100=most volatile in that window).
- Entry (long): hv_percentile <= low_vol_threshold (compression gate) AND
  close breaks above the rolling `donchian_window`-day high (excluding
  today, i.e. prior `donchian_window` bars).
- Exit: close falls below the rolling `donchian_window`-day low, OR
  max_hold_days elapses, whichever first.
- Flat otherwise, long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _hv_percentile(close: pd.Series, vol_window: int, percentile_window: int) -> pd.Series:
    import numpy as np

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)

    def _pct_rank_last(w: np.ndarray) -> float:
        last = w[-1]
        return 100.0 * (w <= last).sum() / len(w)

    pct = realized_vol.rolling(percentile_window, min_periods=vol_window).apply(
        _pct_rank_last, raw=True
    )
    return pct


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    percentile_window: int = 252,
    low_vol_threshold: float = 20.0,
    donchian_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hv_pct = _hv_percentile(close, vol_window, percentile_window)
    compression = hv_pct <= low_vol_threshold

    donchian_high = close.rolling(donchian_window).max().shift(1)
    donchian_low = close.rolling(donchian_window).min().shift(1)

    entry = compression.fillna(False) & (close > donchian_high)
    exit_breakdown = close < donchian_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_breakdown.iloc[i]) or held >= max_hold_days:
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
