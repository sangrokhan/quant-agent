"""Strategy: Jump-Diffusion Momentum (return-jump z-score + ADX/ATR expansion gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-068):
Per PyQuantLab's "Jump-Diffusion Momentum" backtrader strategy
(https://github.com/shortthirdman/TradingStrategies/tree/main/pyquantlab/jump_diffusion_momentum,
read via browser_exec after Medium's own article page 404'd -- the GitHub
repo has the actual disclosed backtrader indicator/strategy source, unlike
the dead article link). Concrete disclosed mechanic, long-only-adapted:

1. JumpDiffusionDetector: z-score today's return against its own rolling
   `lookback`-day realized volatility; `jump_signal = tanh(z / jump_threshold)`
   (bounded [-1,1], saturates when |z| >> jump_threshold), with a
   `min_jump_size` absolute-return floor. `diffusion_trend = tanh(mean(last
   5 returns) / current_vol)` as a secondary momentum-direction proxy.
2. MomentumAfterJump: over a trailing `momentum_period` window, the fraction
   of positive-vs-negative-return days ("momentum_strength"); direction is
   set only if strength >= `momentum_threshold`.
3. TrendVolatilityFilter: both ADX(adx_period) AND ATR(atr_period) must be
   "sustained rising" (majority of the last `rising_lookback` bars
   increasing, plus ADX above `min_adx_level`) -- a volatility/trend-
   EXPANSION gate, distinct from every prior static ADX-threshold or
   ATR-band entry in this repo.
4. Entry (long-only adaptation, no short leg per SAFETY.md): jump_signal >
   `jump_entry_level` (source's own 0.8) AND (momentum direction positive OR
   diffusion_trend * diffusion_weight > 0.1) AND both trend/vol filters
   pass. Exit: `hold_periods` minimum hold enforced, then a trailing stop
   (`trailing_stop_pct`) or hard stop-loss (`stop_loss_pct`) from the
   post-entry running peak, or a `max_hold_days` time-stop backstop.

Distinct from this repo's existing Jump-Weighted Momentum (2026-09-08-151,
reweights formation-window daily returns by magnitude, no z-score jump
DETECTOR or ADX/ATR expansion gate) and every standalone ADX/ATR entry
(none require BOTH indicators to be simultaneously rising, only static
threshold/crossover conditions).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr1 = (high - low)
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, atr


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    jump_threshold: float = 1.5,
    jump_entry_level: float = 0.6,
    min_jump_size: float = 0.01,
    momentum_period: int = 5,
    momentum_threshold: float = 0.6,
    diffusion_weight: float = 0.5,
    adx_period: int = 7,
    atr_period: int = 7,
    min_adx_level: float = 20.0,
    rising_lookback: int = 7,
    min_rising_periods: int = 4,
    hold_periods: int = 7,
    trailing_stop_pct: float = 0.05,
    stop_loss_pct: float = 0.10,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    returns = close.pct_change()
    vol = returns.rolling(lookback).std()
    z = returns / vol.replace(0, np.nan)
    jump_signal = np.tanh(z / jump_threshold)
    jump_size_ok = returns.abs() >= min_jump_size

    diffusion_trend = np.tanh(returns.rolling(5).mean() / vol.replace(0, np.nan))

    pos_frac = (returns > 0).rolling(momentum_period).mean()
    neg_frac = (returns < 0).rolling(momentum_period).mean()
    momentum_strength = pd.concat([pos_frac, neg_frac], axis=1).max(axis=1)
    momentum_direction = np.where(
        momentum_strength >= momentum_threshold,
        np.where(pos_frac > neg_frac, 1, -1),
        0,
    )
    momentum_direction = pd.Series(momentum_direction, index=close.index)

    adx, atr = _adx(high, low, close, adx_period)
    atr_alt = pd.concat([(high - low), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_series = atr_alt.ewm(alpha=1 / atr_period, adjust=False).mean()

    adx_rising = adx.rolling(rising_lookback + 1).apply(
        lambda w: int(sum(w.iloc[i] > w.iloc[i - 1] for i in range(1, len(w))) >= min_rising_periods and w.iloc[-1] >= min_adx_level and w.iloc[-1] > w.iloc[0]),
        raw=False,
    ).fillna(0).astype(bool)
    atr_rising = atr_series.rolling(rising_lookback + 1).apply(
        lambda w: int(sum(w.iloc[i] > w.iloc[i - 1] for i in range(1, len(w))) >= min_rising_periods and w.iloc[-1] > w.iloc[0]),
        raw=False,
    ).fillna(0).astype(bool)

    filters_passed = adx_rising & atr_rising

    long_entry = (
        (jump_signal > jump_entry_level)
        & jump_size_ok
        & ((momentum_direction > 0) | (diffusion_trend * diffusion_weight > 0.1))
        & filters_passed
    ).fillna(False)

    n = len(close)
    close_v = close.to_numpy()
    entry_v = long_entry.to_numpy()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    peak_price = 0.0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            peak_price = max(peak_price, close_v[i])
            trailing_stop_hit = close_v[i] <= peak_price * (1 - trailing_stop_pct)
            hard_stop_hit = close_v[i] <= close_v[entry_idx] * (1 - stop_loss_pct)
            time_stop_hit = held >= max_hold_days
            if held >= hold_periods and (trailing_stop_hit or hard_stop_hit):
                in_position = False
                position.iloc[i] = 0
                continue
            if time_stop_hit:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_v[i]):
                in_position = True
                entry_idx = i
                peak_price = close_v[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
