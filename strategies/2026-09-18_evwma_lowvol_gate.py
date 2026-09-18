"""Strategy: eVWMA price crossover + low-volatility regime gate (rescue
attempt for 2026-09-18-075's consistent near-miss).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix attempt for 2026-09-18-075 (eVWMA price crossover, consistent
Sharpe near-miss across all 4 symbols: QQQ 0.969, SPY 0.991, BTC/USDT
0.991, ETH/USDT 0.773 -- all just below the 1.0 threshold with remarkably
LOW parameter sensitivity, 0.03-0.12). -075's own grid data showed the
edge is heavily concentrated in low-vol regimes (18/24 grid cells passed
in low-vol vs 6/24 mid-vol and 0/24 high-vol) and crypto additionally
failed max drawdown decisively (BTC 0.506, ETH 0.737) -- consistent with
eVWMA's high-volume-driven fast-tracking behavior whipping into large
drawdowns during volume-spike liquidation events in turbulent regimes.

This iteration adds an explicit volatility-regime gate (this repo's
established pattern, e.g. 2026-09-03-001's BB-meanrev-vol-regime
strategy): trade the identical eVWMA crossover signal ONLY when the
20-day realized volatility of the underlying is at or below its own
trailing 1-year median (low/normal-vol regime), flattening out during
high-vol regimes where -075's edge decisively failed. This should trade
off some raw Sharpe (fewer trading opportunities) for a cleaner risk
profile, targeting BOTH the Sharpe near-miss (by excluding the
Sharpe-dragging high-vol periods) and crypto's decisive MDD failure in one
mechanism.

Source: same as 2026-09-18-075
(https://www.luxalgo.com/library/concept/elastic-volume-weighted-ma/) --
the volatility-regime-gate addition is this repo's own established
extension pattern, not separately sourced.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _evwma(close: pd.Series, volume: pd.Series, vol_lookback: int) -> pd.Series:
    n = len(close)
    rolling_vol_sum = volume.rolling(vol_lookback).sum()
    evwma = pd.Series(index=close.index, dtype=float)

    seeded = False
    prev = None
    for i in range(n):
        Nt = rolling_vol_sum.iloc[i]
        Vt = volume.iloc[i]
        Pt = close.iloc[i]
        if not seeded:
            if pd.notna(Nt) and Nt > 0:
                prev = Pt
                seeded = True
                evwma.iloc[i] = prev
            else:
                evwma.iloc[i] = float("nan")
            continue
        if pd.isna(Nt) or Nt <= 0:
            evwma.iloc[i] = prev
            continue
        prev = ((Nt - Vt) * prev + Vt * Pt) / Nt
        evwma.iloc[i] = prev

    return evwma


def generate_signals(
    price_df: pd.DataFrame,
    vol_lookback: int = 20,
    max_hold_days: int = 30,
    vol_regime_window: int = 20,
    vol_regime_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    evwma = _evwma(close, volume, vol_lookback)

    # Volatility regime gate: only trade while 20d realized vol <= its own
    # trailing 1-year median (low/normal-vol regime), this repo's
    # established pattern (see 2026-09-03_bb_meanrev_qqq_volregime.py).
    daily_log_ret = pd.Series(index=close.index, dtype=float)
    ratios = close / close.shift(1)
    for i in range(1, len(close)):
        r = ratios.iloc[i]
        daily_log_ret.iloc[i] = math.log(r) if (r is not None and r > 0) else float("nan")
    realized_vol = daily_log_ret.rolling(vol_regime_window).std()
    trailing_median_vol = realized_vol.rolling(vol_regime_lookback).median()
    low_vol_regime = (realized_vol <= trailing_median_vol * vol_regime_ratio).fillna(False)

    valid = evwma.notna()
    above = (close > evwma) & valid
    above_prev = above.shift(1).fillna(False)
    entry_cross = above & (~above_prev) & low_vol_regime
    exit_cross = ((~above) & above_prev) | (~low_vol_regime)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(df.index)):
        if not in_position:
            if bool(entry_cross.iloc[i]):
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            hold_count += 1
            if bool(exit_cross.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    vol_lookback: int = 20,
    max_hold_days: int = 30,
    vol_regime_window: int = 20,
    vol_regime_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, vol_lookback=vol_lookback, max_hold_days=max_hold_days,
        vol_regime_window=vol_regime_window, vol_regime_lookback=vol_regime_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
