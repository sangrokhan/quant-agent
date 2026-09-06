"""Strategy: Zero-Lag EMA (ZLEMA) fast/slow crossover with a min-hold-days
trade-frequency gate.

Direct fix for near-miss 2026-09-06-170 (ZLEMA/EMA crossover + slope
filter, QQQ Sharpe 0.988 barely missed 1.0 threshold, both QQQ and SPY
failed transaction-cost survival at 406-428 trades over 11.7 years). The
same fix that rescued the Klinger Volume Oscillator near-miss
(2026-09-04-085, "add an explicit min_hold_days gate that ignores exit
signals for the first N days after entry, cutting trade COUNT without
smoothing/blunting the underlying oscillator signal") is applied here:
identical entry/exit crossover logic, but exit signals (reverse cross or
slope turning negative) are ignored for the first min_hold_days bars
after entry -- only the max_hold_days time-stop can force an exit before
that. This directly targets the transaction-cost failure mode (too many
short-lived round-trips) without changing where/why the strategy enters.

Signal logic (identical to 2026-09-06_zlema_ema_crossover_slope.py except
for the min_hold_days gate)
------------------------------------------------------------------------
- fast_zlema: ZLEMA(fast_span) computed on close.
- slow_ema: plain EMA(slow_span) computed on close.
- zlema_slope: fast_zlema.diff(slope_window) > 0.
- Entry (long): fast_zlema crosses above slow_ema AND zlema_slope is
  positive at the crossover bar.
- Exit: only evaluated once held >= min_hold_days: fast_zlema crosses
  back below slow_ema, OR zlema_slope turns negative while still in
  position, OR a max_hold_days time-stop (which fires regardless of
  min_hold_days, as an absolute ceiling on holding period).

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
    fast_span: int = 8,
    slow_span: int = 26,
    slope_window: int = 3,
    min_hold_days: int = 5,
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
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            if held >= min_hold_days and (bool(cross_down.iloc[i]) or bool(slope_falling.iloc[i])):
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
    fast_span: int = 8,
    slow_span: int = 26,
    slope_window: int = 3,
    min_hold_days: int = 5,
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
        min_hold_days=min_hold_days,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
