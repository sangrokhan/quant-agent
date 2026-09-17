"""Strategy: Stochastic Pop (EMA-smoothed %K crossing 55/45 bands) with
EMA200 trend filter and reset hysteresis.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, this iteration):
Per r/pinescript "A trader asked me to combine EMA 200 + Stochastic Pop.
Here's the open-source build." (u/Dependent-Ad6636,
https://www.reddit.com/r/pinescript/comments/1wftf1b/a_trader_asked_me_to_combine_ema_200_stochastic/,
read this iteration via browser_exec after web_search DDGS backend returned
mostly irrelevant results for reddit disclosed-strategy queries), a fully
disclosed MIT-licensed Pine Script combining:
  - Trend filter: price relative to EMA(200), plus whether EMA(200) itself
    is rising (slope > 0).
  - Momentum trigger: "Stochastic Pop" = a 4-period EMA-smoothed %K
    (source's own "EMA 4 on the stochastic line") crossing ABOVE 55 for a
    long signal (mirror: crossing below 45 for short, dropped per SAFETY.md
    long-only requirement).
  - Reset hysteresis: after a long signal fires, the smoothed stochastic
    must first dip back below 45 before another long signal can qualify
    (source's own explicit "Reset" rule) -- prevents re-triggering on every
    tick while the stochastic oscillates above 55.
This is distinct from every prior stochastic-family strategy in this repo
(StochRSI, Stochastic MACD, Stochastic Distance Oscillator, DSS Blau, etc.)
because of the SPECIFIC combination: raw %K (not %D or an RSI-of-stochastic
derivative) smoothed with a short EMA(4), crossing NON-standard 55/45 bands
(not the textbook 80/20 or 70/30), with an explicit below-45-then-above-55
reset hysteresis gate, combined with an EMA200-rising trend filter (not a
simple close>EMA200 static gate).

Signal logic
------------
- ema_trend = EMA(close, trend_len=200); trend_up = close > ema_trend AND
  ema_trend rising (ema_trend > ema_trend.shift(trend_slope_lookback)).
- Raw %K = 100 * (close - LL(stoch_len)) / (HH(stoch_len) - LL(stoch_len))
  over stoch_len (14) days.
- Smoothed %K = EMA(%K, smooth_len=4) (source's own "EMA 4 on stochastic").
- Reset-gated fresh long trigger: smoothed %K crosses above upper_band
  (55), AND smoothed %K dipped below lower_band (45) at some point since
  the last long exit (hysteresis reset, source's own disclosed rule).
- Entry (long): trend_up AND fresh reset-gated trigger.
- Exit: smoothed %K crosses back below lower_band (45) (mirrors the
  source's own reset condition as the natural exit), or max_hold_days
  safety backstop.
- Long-only, flat otherwise, single position at a time.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_len: int = 200,
    trend_slope_lookback: int = 10,
    stoch_len: int = 14,
    smooth_len: int = 4,
    upper_band: float = 55.0,
    lower_band: float = 45.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    ema_trend = close.ewm(span=trend_len, adjust=False).mean()
    trend_up = (close > ema_trend) & (ema_trend > ema_trend.shift(trend_slope_lookback))
    trend_up = trend_up.fillna(False)

    ll = low.rolling(stoch_len, min_periods=stoch_len).min()
    hh = high.rolling(stoch_len, min_periods=stoch_len).max()
    raw_k = 100.0 * (close - ll) / (hh - ll).replace(0, pd.NA)
    raw_k = raw_k.fillna(50.0)
    smooth_k = raw_k.ewm(span=smooth_len, adjust=False).mean()

    cross_up = (smooth_k > upper_band) & (smooth_k.shift(1) <= upper_band)
    cross_down = (smooth_k < lower_band) & (smooth_k.shift(1) >= lower_band)
    cross_up = cross_up.fillna(False)
    cross_down = cross_down.fillna(False)

    pos = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    reset_armed = True  # allow first entry without needing a prior dip below 45
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_pos = False
                reset_armed = True
            else:
                pos.iloc[i] = 1
        else:
            if bool(cross_down.iloc[i]):
                reset_armed = True
            if reset_armed and bool(trend_up.iloc[i]) and bool(cross_up.iloc[i]):
                in_pos = True
                entry_idx = i
                reset_armed = False
                pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_len: int = 200,
    trend_slope_lookback: int = 10,
    stoch_len: int = 14,
    smooth_len: int = 4,
    upper_band: float = 55.0,
    lower_band: float = 45.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position lagged 1 day to avoid look-ahead)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        trend_len=trend_len,
        trend_slope_lookback=trend_slope_lookback,
        stoch_len=stoch_len,
        smooth_len=smooth_len,
        upper_band=upper_band,
        lower_band=lower_band,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
