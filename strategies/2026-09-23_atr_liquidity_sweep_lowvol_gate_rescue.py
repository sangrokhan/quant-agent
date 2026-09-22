"""Strategy: ATR liquidity sweep + horizon confirm, RESCUED with an explicit
low-volatility regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Direct rescue attempt for the near-miss logged this same cron trigger
(2026-09-23-046, ATR-thresholded liquidity sweep with fixed-horizon
reversal confirmation): that strategy's own grid test showed the edge
concentrated in the low-vol tercile (low 17/48 pass vs mid 6/48, high
12/48 in the 3-way vol split) yet its full-sample (unsliced) Sharpe on the
best per-symbol config (SPY, swing_window=20/poke_atr_mult=0.3/
confirm_bars=3) was only 0.880 -- below the 1.0 threshold -- because
trading through the mid/high-vol regimes drags down the blended Sharpe.
This iteration adds the identical low-vol realized-vol gate construction
already used successfully elsewhere in this repo (20d realized vol <=
vol_regime_ratio x trailing 252d median, e.g.
strategies/2026-09-03_bb_meanrev_qqq_volregime.py and the accepted
2026-09-20-140 RSI(2)+ATR% gate) ON TOP of the unchanged sweep-confirm
entry/exit logic, restricting entries to the low-vol regime only. No new
external source this iteration -- pure internal-KB parameter/construction
follow-up per RESEARCH_LOOP.md's allowance for "regime-gate rescue
attempts" on a flagged near-miss.

Signal logic
------------
Identical to strategies/2026-09-23_atr_liquidity_sweep_horizon_confirm.py
(swing-low poke in ATR units, close-back-inside confirmation within
confirm_bars, max_hold_days time-stop, close>SMA200 uptrend gate) PLUS:
an additional low_vol_regime gate (20d realized vol of the underlying
close <= vol_regime_ratio * trailing 252d rolling median) required at both
the poke bar AND the confirmation bar for entry to fire.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 20,
    poke_atr_mult: float = 0.3,
    confirm_bars: int = 3,
    max_hold_days: int = 8,
    atr_window: int = 14,
    trend_window: int = 200,
    trend_filter: bool = True,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(close)

    swing_low = low.rolling(swing_window).min().shift(1)
    atr = _atr(df, atr_window)
    poke = (low < (swing_low - poke_atr_mult * atr)).fillna(False)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    low_vol = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = bool(close.iloc[i] < swing_low.iloc[i]) if pd.notna(swing_low.iloc[i]) else False
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        if bool(poke.iloc[i]) and pd.notna(swing_low.iloc[i]) and bool(uptrend.iloc[i]) and bool(low_vol.iloc[i]):
            level = swing_low.iloc[i]
            confirmed_at = None
            for j in range(i, min(i + confirm_bars + 1, n)):
                if close.iloc[j] > level and bool(low_vol.iloc[j]):
                    confirmed_at = j
                    break
            if confirmed_at is not None:
                in_position = True
                entry_idx = confirmed_at
                i = confirmed_at
                position.iloc[i] = 1
                i += 1
                continue
        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
