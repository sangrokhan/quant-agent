"""Strategy: Elder Force Index (2-period EMA) zero-line cross, gated by
a Schaff Trend Cycle (STC) primary-trend confirmation (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-086):
Per AlphaX Trading's Force Index quant-library page: "Enter a long position
when the 2-period Force Index crosses above the zero line, provided the
primary trend is confirmed by the STC." This combines the fast Force Index
(short-term buying/selling pressure, (Close-PrevClose)*Volume, 2-period EMA
smoothed) as the ENTRY TRIGGER with STC>50 (this repo's existing
2026-09-04-080 STC construction) as the TREND CONFIRMATION GATE -- distinct
from all prior Force Index strategies in this repo: dual-EMA(2/13)
pullback-continuation (2026-09-04-049), bullish divergence
(2026-09-05-048), and MACD-histogram "triple screen" trend confirmation
(2026-09-09-007, rejected) -- this is the first to pair Force Index
specifically with STC (a genuinely different trend-confirmation
construction than a raw MACD histogram).

Signal logic
------------
- Raw Force Index = (Close - PrevClose) * Volume; FI(fi_span) = EMA(Raw FI,
  fi_span) (source's own 2-period default).
- STC(stc_fast, stc_slow, stc_cycle, stc_factor): this repo's existing
  double-stochastic-smoothed-MACD construction (see
  2026-09-04_schaff_trend_cycle.py for the reference implementation,
  reused here).
- Entry (long): FI crosses from <=0 to >0 (fresh bullish cross) AND
  STC > stc_centerline (primary trend confirmed bullish) at that bar.
- Exit: FI crosses back below 0, OR STC drops back below stc_centerline
  (trend confirmation breaks), OR a max_hold_days time-stop.
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


def _force_index(df: pd.DataFrame, fi_span: int) -> pd.Series:
    close, volume = df["close"], df["volume"]
    raw_fi = close.diff() * volume
    return raw_fi.ewm(span=fi_span, adjust=False, min_periods=fi_span).mean()


def _stoch_of_series(series: pd.Series, cycle: int) -> pd.Series:
    lo = series.rolling(cycle).min()
    hi = series.rolling(cycle).max()
    rng = (hi - lo).replace(0, pd.NA)
    return 100.0 * (series - lo) / rng


def _stc(close: pd.Series, fast: int, slow: int, cycle: int, factor: float) -> pd.Series:
    macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()

    k1 = _stoch_of_series(macd, cycle).fillna(0.0)
    d1 = pd.Series(index=close.index, dtype=float)
    prev = 0.0
    for i in range(len(d1)):
        prev = prev + factor * (k1.iloc[i] - prev)
        d1.iloc[i] = prev

    k2 = _stoch_of_series(d1, cycle).fillna(0.0)
    stc = pd.Series(index=close.index, dtype=float)
    prev = 0.0
    for i in range(len(stc)):
        prev = prev + factor * (k2.iloc[i] - prev)
        stc.iloc[i] = prev

    return stc


def generate_signals(
    price_df: pd.DataFrame,
    fi_span: int = 2,
    stc_fast: int = 23,
    stc_slow: int = 50,
    stc_cycle: int = 10,
    stc_factor: float = 0.5,
    stc_centerline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fi = _force_index(df, fi_span)
    stc = _stc(close, stc_fast, stc_slow, stc_cycle, stc_factor)

    prev_fi = fi.shift(1)
    bullish_cross = (fi > 0) & (prev_fi <= 0)
    bearish_cross = (fi < 0) & (prev_fi >= 0)
    trend_confirmed = stc > stc_centerline

    entry = bullish_cross & trend_confirmed.fillna(False)
    exit_trend_break = stc < stc_centerline

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
