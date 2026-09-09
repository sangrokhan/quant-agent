"""Strategy: Detrended Synthetic Price (DSP), zero-line cross with
Instantaneous-Trendline slope confirmation, 200-SMA trend filter
(long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-076):
Per AlphaX Trading's Detrended Synthetic Price dictionary entry
(https://alphax.trading/dictionary/detrended-synthetic-price, browser_exec
fallback -- web_search DDGS errored/returned no results for the direct
query), DSP = Price - Instantaneous Trendline (ITL, an Ehlers-style
recursive high-pass/low-pass filter pair that extracts a smoothed trend
component while suppressing cycle-period noise). The source's own
"Execution Rules for Systematic Traders": Long entry when DSP crosses
above zero AND the ITL is sloping upward; exit when DSP reaches a
historical extreme or reverses; trend filter = only trade in the direction
of a 200-period SMA; avoid entries when DSP is stagnant near zero. This is
distinct from all 4 existing repo DPO (Detrended Price Oscillator)
strategies, which use the simpler DPO formula (price minus a
BACKWARD-SHIFTED simple moving average) rather than an Ehlers
instantaneous-trendline high-pass construction, and none of the existing
DPO variants require an explicit ITL-slope confirmation alongside the
zero-cross.

Instantaneous Trendline formula (simplified Ehlers 2-pole recursive
filter, alpha derived from filter_period):
    alpha = 2 / (filter_period + 1)
    ITL[i] = (alpha - alpha^2/4) * price[i]
             + 0.5*alpha^2 * price[i-1]
             - (alpha - 0.75*alpha^2) * price[i-2]
             + 2*(1-alpha) * ITL[i-1]
             - (1-alpha)^2 * ITL[i-2]
    (first two bars initialized to price itself, standard Ehlers warm-up.)

Signal logic
------------
- price = (high + low + close) / 3 (typical price, per source's own "usually
  the mean of the High, Low, and Close prices").
- DSP = price - ITL.
- ITL slope: ITL[i] > ITL[i - itl_slope_lookback] (sloping upward).
- Zero-line stagnation filter: |DSP| over the recent `stagnant_lookback`
  bars must have exceeded `stagnant_threshold_pct` of price at least once
  (avoid entries when DSP is flat/near-zero, per source's own caveat).
- 200-SMA trend filter: close > SMA(trend_window).
- Entry (long): DSP crosses above zero (fresh cross) AND ITL sloping
  upward AND not stagnant AND trend filter satisfied.
- Exit: DSP crosses back below zero, OR a `max_hold_days` time-stop
  (source's "historical extreme" exit isn't reproducible as a precise
  rule without a reference window; this repo substitutes a time-stop per
  its consistent convention).
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


def _instantaneous_trendline(price: pd.Series, filter_period: int) -> pd.Series:
    alpha = 2.0 / (filter_period + 1.0)
    n = len(price)
    itl = [None] * n
    p = price.values
    for i in range(n):
        if i < 2:
            itl[i] = p[i]
        else:
            itl[i] = (
                (alpha - alpha ** 2 / 4.0) * p[i]
                + 0.5 * alpha ** 2 * p[i - 1]
                - (alpha - 0.75 * alpha ** 2) * p[i - 2]
                + 2.0 * (1.0 - alpha) * itl[i - 1]
                - (1.0 - alpha) ** 2 * itl[i - 2]
            )
    return pd.Series(itl, index=price.index, dtype=float)


def generate_signals(
    price_df: pd.DataFrame,
    filter_period: int = 20,
    itl_slope_lookback: int = 5,
    stagnant_lookback: int = 10,
    stagnant_threshold_pct: float = 0.005,
    trend_window: int = 200,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0

    itl = _instantaneous_trendline(typical_price, filter_period)
    dsp = typical_price - itl

    itl_slope_up = itl > itl.shift(itl_slope_lookback)

    dsp_pct = (dsp.abs() / typical_price)
    not_stagnant = (
        dsp_pct.rolling(stagnant_lookback, min_periods=1).max() > stagnant_threshold_pct
    )

    trend_sma = close.rolling(trend_window).mean()
    trend_filter = close > trend_sma

    cross_up = (dsp > 0) & (dsp.shift(1) <= 0)
    cross_down = (dsp < 0) & (dsp.shift(1) >= 0)

    entry = (
        cross_up
        & itl_slope_up.fillna(False)
        & not_stagnant.fillna(False)
        & trend_filter.fillna(False)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
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
