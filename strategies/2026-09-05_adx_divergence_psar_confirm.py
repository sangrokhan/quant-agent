"""Strategy: ADX bullish divergence confirmed by a Parabolic SAR bullish
flip, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-082):
Per a GS Trading social-media strategy concept ("ADX Divergence + Parabolic
SAR Trading Strategy") combined with the standard divergence definition
(trendllylab.com: "Bullish divergence: price makes a lower low, but the
indicator makes a higher low. Selling pressure is weakening; a bottom may
be near."): ADX (Wilder's Average Directional Index, a NON-directional
0-100 trend-STRENGTH measure) making a higher low while price makes a new
swing low signals that the prior downtrend's strength/momentum is fading
(even though ADX itself doesn't indicate direction) -- a bottoming
precursor. Because ADX is direction-agnostic, this divergence alone cannot
confirm an upward reversal, so entry additionally requires a Parabolic SAR
bullish flip (SAR crosses to below price) as the directional confirmation
trigger, per the source's own two-indicator combination. This is the first
ADX DIVERGENCE strategy in this repo -- prior ADX entries
(2026-09-03-017, 2026-09-04-087/122/162, 2026-09-05-062) all used ADX as a
trend-strength GATE/threshold alongside a directional signal (DMI
crossover, Bollinger touch, DPO), never a divergence (price-vs-ADX
shape) construction.

Signal logic
------------
- ADX(adx_window): Wilder's directional index (via smoothed +DM/-DM/TR).
- Parabolic SAR(af_start, af_step, af_max): standard recursive SAR.
- Bullish divergence check: close makes a new swing_lookback-bar low AND
  ADX's own swing_lookback-bar low is HIGHER than ADX's rolling low from
  the prior occurrence (trend strength did not confirm the new price low).
- Entry (long): a bullish divergence was flagged within divergence_recency
  bars AND Parabolic SAR flips bullish (close crosses above SAR) at or
  after the divergence.
- Exit: Parabolic SAR flips bearish (close crosses back below SAR), or a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [high - low, (high - prior_close).abs(), (low - prior_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
    plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / window, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / window, adjust=False).mean()

    plus_di = 100.0 * plus_dm_s / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm_s / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / window, adjust=False).mean()
    return adx.fillna(0.0)


def _parabolic_sar(
    df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
) -> pd.Series:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    sar = [None] * n
    if n == 0:
        return pd.Series(sar, index=df.index, dtype=float)

    trend_up = True
    sar_val = low[0]
    ep = high[0]
    af = af_start
    sar[0] = sar_val

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

    return pd.Series(sar, index=df.index, dtype=float)


def generate_signals(
    price_df: pd.DataFrame,
    adx_window: int = 14,
    swing_lookback: int = 10,
    divergence_recency: int = 10,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    adx = _adx(df, adx_window)
    sar = _parabolic_sar(df, af_start=af_start, af_step=af_step, af_max=af_max)

    price_rolling_low = close.rolling(swing_lookback).min()
    adx_rolling_low = adx.rolling(swing_lookback).min()

    price_is_new_low = close <= price_rolling_low
    adx_low_prior = adx_rolling_low.shift(swing_lookback)
    bullish_divergence = price_is_new_low & (adx_rolling_low > adx_low_prior)

    divergence_recent = bullish_divergence.rolling(divergence_recency, min_periods=1).max().astype(bool)

    sar_bull_flip = (close > sar) & (close.shift(1) <= sar.shift(1))
    sar_bear_flip = (close < sar) & (close.shift(1) >= sar.shift(1))

    entry = divergence_recent.fillna(False) & sar_bull_flip.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    exit_vals = sar_bear_flip.fillna(False).to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
