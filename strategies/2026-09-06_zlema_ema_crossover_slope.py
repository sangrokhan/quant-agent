"""Strategy: Zero-Lag EMA (ZLEMA) fast/slow crossover with slope filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
John Ehlers' Zero-Lag EMA (Rocket Science for Traders, 2001; also
attributed to Ehlers & Ulrich 2000) removes the inherent lag of a plain
EMA by adding back an estimate of the lag-induced error before smoothing:
ZLEMA = EMA(2*price - price.shift(lag)), lag = (span-1)/2 (rounded).
Per this iteration's Google AI-overview synthesis of TrendSpider/LuxAlgo/
ArrowAlgo ZLEMA-strategy guides: long entry when a FAST ZLEMA crosses
above a SLOWER standard EMA, provided the fast ZLEMA's own slope is
rising (an extra confirmation filter to avoid whipsaw crossovers in a
flat/choppy market); exit on the reverse crossover (fast ZLEMA back below
slow EMA) or when the slope filter itself flips negative while still
above the slow EMA (an early trend-weakening exit). This is a fresh
trend-following crossover construction distinct from every other
crossover strategy in this repo -- no prior ZLEMA entry exists in
strategies_index.jsonl (checked at Step 1/3).

Signal logic
------------
- fast_zlema: ZLEMA(fast_span) computed on close.
- slow_ema: plain EMA(slow_span) computed on close (source's own
  "vs a slower standard EMA" framing, not a second ZLEMA).
- zlema_slope: fast_zlema.diff(slope_window) > 0 (rising over the last
  slope_window bars).
- Entry (long): fast_zlema crosses above slow_ema AND zlema_slope is
  positive at the crossover bar.
- Exit: fast_zlema crosses back below slow_ema, OR zlema_slope turns
  negative while still in position (early trend-weakening exit), OR a
  max_hold_days time-stop (avoid indefinite holds through a slow chop).

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


def _zlema(series: pd.Series, span: int) -> pd.Series:
    """Zero-Lag EMA: EMA of (2*price - price.shift(lag)), lag=(span-1)//2."""
    lag = max(1, (span - 1) // 2)
    de_lagged = 2 * series - series.shift(lag)
    return de_lagged.ewm(span=span, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
    slope_window: int = 3,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_zlema = _zlema(close, fast_span)
    slow_ema = close.ewm(span=slow_span, adjust=False).mean()
    slope_rising = fast_zlema.diff(slope_window) > 0

    above = fast_zlema > slow_ema
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & (above.shift(1).fillna(False))

    entry = cross_up & slope_rising.fillna(False)
    slope_falling = ~slope_rising.fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or bool(slope_falling.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
    slope_window: int = 3,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns: position (lagged by 1 bar to avoid
    lookahead) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        fast_span=fast_span,
        slow_span=slow_span,
        slope_window=slope_window,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
