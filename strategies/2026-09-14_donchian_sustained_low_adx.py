"""Strategy: Donchian channel breakout gated by a SUSTAINED (multi-bar
persistence) LOW-ADX consolidation filter, refining 2026-09-14-116's
single-bar low-ADX gate.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-118):
Follow-up to this cron trigger's own iterations 2026-09-14-116 (Donchian
breakout gated by ADX(14) being below a threshold on a SINGLE prior bar,
QQQ accepted / SPY near-miss / crypto decisively rejected via turnover
explosion: 1535 trades) and 2026-09-14-117 (own data analysis, not an
external source: BTC/USDT actually spends ~49.5% of time with ADX(14)<25,
similar to QQQ's 58.7% -- crypto is NOT rarely quiet, so the single-bar
low-ADX gate's failure to suppress crypto entries is likely because
crypto's sub-threshold ADX readings are brief/choppy dips rather than
sustained multi-day consolidations, unlike equities' typically longer
quiet stretches).

This iteration tests that refinement directly: require ADX(14) to have
stayed at/below adx_max for AT LEAST `min_consolidation_bars` consecutive
bars immediately before the breakout (not just the single bar right
before it), filtering for genuine sustained coils rather than any
momentary dip. Same Donchian breakout entry + Chandelier-Exit-style
ratcheting ATR trailing stop exit as 2026-09-14-116, isolating the effect
of the persistence requirement alone.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    atr = _atr(high, low, close, period)
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr)

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    donchian_window: int = 25,
    adx_period: int = 14,
    adx_max: float = 25.0,
    min_consolidation_bars: int = 5,
    atr_period: int = 14,
    atr_multiplier: float = 3.0,
) -> pd.Series:
    """Long-only 0/1 exposure: enter when close breaks above the prior
    N-day Donchian high AND ADX has stayed at/below adx_max for at least
    `min_consolidation_bars` consecutive bars immediately before the
    breakout (sustained consolidation, not just a single quiet bar);
    exit via a monotonically-ratcheting ATR trailing stop."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    donchian_high = close.rolling(donchian_window).max().shift(1)
    adx = _adx(high, low, close, adx_period).shift(1)

    below = (adx <= adx_max).astype(int)
    sustained_low_adx = below.rolling(min_consolidation_bars).sum() >= min_consolidation_bars

    atr = _atr(high, low, close, atr_period)

    breakout = (close > donchian_high) & sustained_low_adx.fillna(False)

    n = len(close)
    c = close.to_numpy()
    b = breakout.fillna(False).to_numpy()
    a = atr.to_numpy()

    position = np.zeros(n)
    stop = np.nan
    in_pos = False
    for i in range(n):
        if not in_pos:
            if b[i]:
                in_pos = True
                stop = c[i] - atr_multiplier * a[i] if not np.isnan(a[i]) else -np.inf
        else:
            if not np.isnan(a[i]):
                stop = max(stop, c[i] - atr_multiplier * a[i])
            if c[i] < stop:
                in_pos = False
                stop = np.nan
        position[i] = 1.0 if in_pos else 0.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    donchian_window: int = 25,
    adx_period: int = 14,
    adx_max: float = 25.0,
    min_consolidation_bars: int = 5,
    atr_period: int = 14,
    atr_multiplier: float = 3.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        donchian_window=donchian_window,
        adx_period=adx_period,
        adx_max=adx_max,
        min_consolidation_bars=min_consolidation_bars,
        atr_period=atr_period,
        atr_multiplier=atr_multiplier,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
