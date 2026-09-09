"""Strategy: Parabolic SAR bullish flip, gated by an ADX trend-strength
threshold (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-072):
Per Unofficed's "Combining Parabolic SAR with ADX" lesson
(https://unofficed.com/courses/entropy/lessons/combining-parabolic-sar-with-adx/,
browser_exec fallback -- web_search DDGS returned no results for the direct
query), the disclosed rule stack is: (1) ADX must be greater than 25,
confirming sufficient trend strength, before taking any signal, and (2) the
entry trigger is the Parabolic SAR flipping from above price to below price
(bullish flip) while the ADX filter is satisfied. This is a simple
threshold-gate combination, distinct from this repo's existing Parabolic
SAR strategies: 2026-09-04-042 uses an SMA trend filter (not ADX) and
2026-09-05-082 uses ADX DIVERGENCE (price-vs-ADX shape pattern) rather than
a plain ADX-level threshold gate on the SAR flip itself.

Parabolic SAR formula (standard Wilder, reused construction from
2026-09-04_parabolic_sar_trend_filter.py): sequential/path-dependent,
computed with an explicit loop.

ADX formula (standard Wilder): smoothed +DM/-DM/True Range -> +DI/-DI ->
DX = 100 * |+DI - -DI| / (+DI + -DI) -> ADX = Wilder-smoothed DX.

Signal logic
------------
- Entry (long): Parabolic SAR flips from above price to below price
  (bullish flip, fresh bar) AND ADX(adx_window) > adx_threshold at that
  bar.
- Exit: Parabolic SAR flips back to above price (bearish flip), OR a
  `max_hold_days` time-stop (source doesn't specify an ADX-based exit;
  this repo consistently adds a time-stop safety net).
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


def _parabolic_sar_and_trend(
    df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
):
    """Return (sar_series, trend_up_series) aligned to df.index."""
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    sar = [None] * n
    trend_flags = [None] * n
    if n == 0:
        return pd.Series(sar, index=df.index, dtype=float), pd.Series(trend_flags, index=df.index)

    trend_up = True
    sar_val = low[0]
    ep = high[0]
    af = af_start
    sar[0] = sar_val
    trend_flags[0] = trend_up

    for i in range(1, n):
        prev_sar = sar_val
        sar_val = prev_sar + af * (ep - prev_sar)

        if trend_up:
            sar_val = min(sar_val, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < sar_val:
                trend_up = False
                sar_val = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            sar_val = max(sar_val, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > sar_val:
                trend_up = True
                sar_val = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        sar[i] = sar_val
        trend_flags[i] = trend_up

    return pd.Series(sar, index=df.index, dtype=float), pd.Series(trend_flags, index=df.index)


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    tr1 = (high - low)
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    dx = dx.fillna(0.0)
    adx = dx.ewm(alpha=1.0 / window, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sar, trend_up = _parabolic_sar_and_trend(df, af_start=af_start, af_step=af_step, af_max=af_max)
    adx = _adx(df, adx_window)

    bullish_flip = trend_up.astype(bool) & (~trend_up.shift(1).fillna(False).astype(bool))
    bearish_flip = (~trend_up.astype(bool)) & (trend_up.shift(1).fillna(True).astype(bool))

    entry = bullish_flip & (adx > adx_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_flip.iloc[i]) or held >= max_hold_days:
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
