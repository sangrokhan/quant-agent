"""Strategy: Crypto-focused z-score mean reversion, triple-gated by
ADX weak-trend + Bollinger-Band-width contraction ("range-bound regime").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-056):
Per xerogravity.com's "Crypto Mean Reversion Strategy" guide (visited this
iteration): mean reversion in crypto only works in a specific "habitat" --
"Price is range-bound... volatility is elevated but stabilizing... "
The source's own three concrete regime filters: "ADX below 20 on the
daily -- signals weak trend, favors reversion" and "Bollinger Band width
contracting over the last 10 periods -- range tightening", combined with
a z-score entry ("Z-score trading crypto setups typically use thresholds
of +/-2.0 for entries and +/-0.5 for exits").

This combines all three filters (z-score level + ADX weak-trend gate +
BB-width contraction gate) simultaneously -- distinct from this repo's
existing 2026-09-08-002 (which used %-distance-from-MA + ADX gate ONLY,
no z-score, no BB-width filter) and 2026-09-04-082 (plain z-score, no
regime gates at all). First triple-filter (z-score + ADX + BB-width)
mean-reversion construction in this repo, and explicitly crypto-motivated
by a crypto-specific source (most prior mean-reversion regime-gate
strategies in this repo were equity-first with crypto as an afterthought).

Signal logic
------------
- z = (close - SMA(z_window)) / STD(z_window)
- adx = ADX(adx_window) (Wilder's, computed from +DI/-DI)
- bb_width = (upper_band - lower_band) / SMA(z_window), where bands are
  SMA +/- 2*STD over the same z_window; "contracting" = bb_width's
  bb_contraction_lookback-bar trailing mean is falling (today's bb_width
  <= its value bb_contraction_lookback bars ago).
- Entry (long): z <= -entry_z (oversold) AND adx <= adx_max (weak trend)
  AND bb_width contracting.
- Exit: z >= -exit_z (reverted), OR adx > adx_max (regime flip), OR a
  max_hold_days time-stop.

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


def _adx(df: pd.DataFrame, n: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean() / atr.replace(0, pd.NA)
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean() / atr.replace(0, pd.NA)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = dx.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    z_window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    adx_window: int = 14,
    adx_max: float = 20.0,
    bb_contraction_lookback: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(z_window).mean()
    std = close.rolling(z_window).std()
    z = (close - sma) / std.replace(0, pd.NA)

    bb_width = (4 * std) / sma.replace(0, pd.NA)
    bb_contracting = bb_width <= bb_width.shift(bb_contraction_lookback)

    adx = _adx(df, adx_window)
    weak_trend = adx <= adx_max

    entry_cond = (z <= -entry_z) & weak_trend.fillna(False) & bb_contracting.fillna(False)
    exit_reverted = z >= -exit_z

    n = len(df)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            regime_flip = not bool(weak_trend.iloc[i]) if pd.notna(weak_trend.iloc[i]) else False
            reverted = bool(exit_reverted.iloc[i]) if pd.notna(exit_reverted.iloc[i]) else False
            if reverted or regime_flip or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]) if pd.notna(entry_cond.iloc[i]) else False:
                in_pos = True
                hold_count = 0
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
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
