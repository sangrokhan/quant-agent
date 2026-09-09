"""Strategy: Parabolic SAR + ADX threshold gate, WITH an explicit ATR
stop-loss added on top of the SAR trailing exit (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-073):
Direct follow-up to near-miss 2026-09-09-072 (plain PSAR+ADX-threshold-gate,
rejected -- QQQ full-sample Sharpe 0.994 near-miss but max_drawdown 37.2%
decisively failed). That entry's own notes flagged the SAR-flip-only exit
(no price-structure stop beyond the trailing SAR line, which can be very
far from price during a fast adverse move before the next SAR update) as
the likely drawdown driver, and suggested "a future revisit could add an
explicit ATR-based stop-loss on top of the SAR trailing exit to cap
drawdown, since the underlying Sharpe is genuinely close to the
threshold." This strategy implements exactly that fix: identical PSAR+ADX
entry logic, but the exit additionally triggers whenever price closes
below (entry_price - atr_stop_multiplier * ATR_at_entry), a fixed
volatility-scaled stop-loss from the entry price, in addition to the
existing SAR-flip and time-stop exits.

Signal logic
------------
- Entry (long): identical to 2026-09-09-072 -- Parabolic SAR flips
  bullish (fresh bar) AND ADX(adx_window) > adx_threshold.
- Exit: Parabolic SAR flips bearish, OR close drops below
  (entry_price - atr_stop_multiplier * ATR(atr_window) as of entry day)
  [the new fixed volatility stop-loss], OR a `max_hold_days` time-stop.
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = (high - low)
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
    adx_window: int = 14,
    adx_threshold: float = 20.0,
    atr_window: int = 14,
    atr_stop_multiplier: float = 3.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sar, trend_up = _parabolic_sar_and_trend(df, af_start=af_start, af_step=af_step, af_max=af_max)
    adx = _adx(df, adx_window)
    atr = _atr(df, atr_window)

    bullish_flip = trend_up.astype(bool) & (~trend_up.shift(1).fillna(False).astype(bool))
    bearish_flip = (~trend_up.astype(bool)) & (trend_up.shift(1).fillna(True).astype(bool))

    entry = bullish_flip & (adx > adx_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_stop = close.iloc[i] < stop_level if stop_level is not None else False
            if bool(bearish_flip.iloc[i]) or hit_stop or held >= max_hold_days:
                in_position = False
                stop_level = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                atr_at_entry = atr.iloc[i]
                stop_level = close.iloc[i] - atr_stop_multiplier * atr_at_entry if pd.notna(atr_at_entry) else None
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
