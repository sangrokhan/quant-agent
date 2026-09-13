"""Strategy: Donchian channel breakout gated by a LOW-ADX consolidation
filter (contrarian use of ADX vs the repo's usual high-ADX confirmation),
continuous exposure via ATR-based ratcheting trailing stop.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-116):
Source: https://www.quantifiedstrategies.com/how-we-built-bitcoin-trend-following-strategy/
The article describes a Donchian breakout system where entries are gated by
ADX(14) BEING BELOW a threshold (25) rather than above it -- the opposite of
this repo's usual "ADX>threshold confirms strong trend" gate (see
2026-09-03-017, 2026-09-04-087, 2026-09-04-162, 2026-09-06-098, etc, all of
which required ADX ABOVE a threshold). The article's rationale: Bitcoin
(and trending assets generally) often coil in a low-volatility/low-ADX
consolidation BEFORE an explosive breakout, so requiring LOW ADX at entry
time selects for "quiet before the storm" setups rather than confirming an
already-established trend (which risks entering late, after much of the
move has already happened). Author reports (unverified, own backtest)
CAGR 90% vs 66% buy-and-hold, 35 trades, 63% win rate on BTC/USD since 2015.

Repo has 34 prior ADX entries, all using ADX as a HIGH-threshold trend
CONFIRMATION filter (paired with various entry signals) -- none tested ADX
as a LOW-threshold pre-breakout CONSOLIDATION filter specifically paired
with a Donchian breakout entry. This iteration implements exactly that:
long entry when close breaks the N-day Donchian high AND ADX(14) was below
adx_max at the time just before the breakout (i.e. the setup was quiet),
with a continuous exposure sized via a monotonically-ratcheting ATR
trailing stop distance (position held at 1.0 while price stays above the
ratcheting stop, exits to 0 when price crosses below it) -- reusing this
repo's established Chandelier-Exit-style ratcheting-stop construction
(already validated e.g. in 2026-09-11-014's isolated AdaptiveTrend
replication) rather than the article's simple "N-day low" fixed exit.

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
    """Wilder's ADX. Standard construction: smoothed +DM/-DM divided by ATR
    give +DI/-DI; ADX is the smoothed absolute normalized DI difference."""
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
    donchian_window: int = 15,
    adx_period: int = 14,
    adx_max: float = 25.0,
    atr_period: int = 14,
    atr_multiplier: float = 3.0,
) -> pd.Series:
    """Long-only 0/1 exposure: enter when close breaks above the prior
    N-day Donchian high AND ADX (measured on the PRIOR bar, before the
    breakout) is at/below adx_max (a quiet/consolidating setup); exit via a
    monotonically-ratcheting ATR trailing stop (Chandelier-Exit style)
    once in a position."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    donchian_high = close.rolling(donchian_window).max().shift(1)
    adx = _adx(high, low, close, adx_period).shift(1)
    atr = _atr(high, low, close, atr_period)

    breakout = (close > donchian_high) & (adx <= adx_max)

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
    donchian_window: int = 15,
    adx_period: int = 14,
    adx_max: float = 25.0,
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
        atr_period=atr_period,
        atr_multiplier=atr_multiplier,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
