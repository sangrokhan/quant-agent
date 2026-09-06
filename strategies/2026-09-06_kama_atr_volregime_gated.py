"""Strategy: KAMA + ATR volatility-band trend-following, gated by an explicit
realized-volatility regime filter (low-vol tercile only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-183):
Direct follow-up to near-miss 2026-09-06-181 (plain KAMA/ATR-band
crossover, full-sample SPY Sharpe 0.894 vs 1.0 threshold -- a near-miss
whose Step 6 grid showed the edge was almost entirely concentrated in the
low-volatility tercile: 8/16 low-vol grid cells passed vs only 1/16
high-vol cells). This iteration tests whether adding an EXPLICIT
realized-volatility regime gate (20-day realized vol <= its trailing 1-year
median, the same construction already validated as useful in this repo's
accepted `2026-09-03_bb_meanrev_qqq_volregime.py`) on top of the identical
KAMA-crossover/ATR-band entry logic rescues the near-miss by restricting
trading to the regime where the edge was already shown to concentrate,
rather than relying on the ATR-percent band alone (which only measures
short-window ATR, not a regime-relative measure) to do that filtering.

Signal logic
------------
Identical KAMA/ATR entry logic to 2026-09-06_kama_atr_volband.py, PLUS:
- 20-day realized volatility (std of daily log returns, annualized) vs its
  trailing 252-day median -> "low-vol regime" when current 20d vol <=
  vol_regime_ratio x that median.
- Entry (long): close crosses above KAMA AND atr_pct in
  [atr_min_pct, atr_max_pct] AND low_vol_regime.
- Exit: close crosses below KAMA, OR atr_pct > atr_exit_pct, OR the
  volatility regime flips to high-vol (new: risk-off exit, mirrors the
  accepted bb_meanrev strategy's regime-flip exit), OR max_hold_days.
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


def _kama(close: pd.Series, er_window: int, fast_sc_period: int, slow_sc_period: int) -> pd.Series:
    change = (close - close.shift(er_window)).abs()
    volatility = close.diff().abs().rolling(er_window).sum()
    er = (change / volatility.replace(0.0, pd.NA)).fillna(0.0)

    fast_sc = 2.0 / (fast_sc_period + 1)
    slow_sc = 2.0 / (slow_sc_period + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = pd.Series(index=close.index, dtype=float)
    first_valid = close.first_valid_index()
    if first_valid is None:
        return kama
    start_pos = close.index.get_loc(first_valid)
    kama.iloc[start_pos] = close.iloc[start_pos]
    for i in range(start_pos + 1, len(close)):
        prev = kama.iloc[i - 1]
        if pd.isna(prev):
            kama.iloc[i] = close.iloc[i]
            continue
        sc_i = sc.iloc[i]
        if pd.isna(sc_i):
            sc_i = slow_sc ** 2
        kama.iloc[i] = prev + sc_i * (close.iloc[i] - prev)
    return kama


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_sc_period: int = 2,
    slow_sc_period: int = 30,
    atr_window: int = 14,
    atr_min_pct: float = 0.005,
    atr_max_pct: float = 0.035,
    atr_exit_pct: float = 0.06,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kama = _kama(close, er_window, fast_sc_period, slow_sc_period)
    atr = _atr(df, atr_window)
    atr_pct = (atr / close).fillna(0.0)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    above = close > kama
    cross_up = above & ~above.shift(1).fillna(False)
    cross_down = (~above) & above.shift(1).fillna(False)

    vol_ok = (atr_pct >= atr_min_pct) & (atr_pct <= atr_max_pct)
    vol_spike = atr_pct > atr_exit_pct

    entry = cross_up & vol_ok & low_vol_regime
    exit_regime_flip = ~low_vol_regime

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(cross_down.iloc[i])
                or bool(vol_spike.iloc[i])
                or bool(exit_regime_flip.iloc[i])
                or held >= max_hold_days
            ):
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
