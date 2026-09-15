"""Strategy: SMA(trend_window) directional gate with continuous TD REI
(DeMark Range Expansion Index) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix attempt for prior id 2026-09-16-121 (TD REI oversold-bounce
binary threshold-cross trigger, rejected across all symbols -- QQQ strong
Sharpe/MDD but decisive parameter-sensitivity fail 0.622>0.5 genuine
overfitting flag; SPY decisive Sharpe+TC fail; BTC/USDT decisive Sharpe+MDD
fail; ETH/USDT passed 4/5 validators, MDD near-missed 0.253 vs 0.25
threshold). Per https://www.linnsoft.com/techind/demark-range-expansion-index
(exact formula, already in this repo's ledger) and
https://www.quantifiedstrategies.com/range-expansion-index/ (interpretation).

TD REI = 100 * SUM(VALUE,N) / SUM(ABSVALUE,N) is ALREADY naturally bounded
in [-100, +100] by construction (a ratio, like %B or BVC) -- no z-score/tanh
needed, only a /100 rescale. This sub-iteration reuses the identical REI
formula (unchanged) but reframes it as a CONTINUOUS SIZING dial: REI/100
used directly as the sizing signal inside an SMA(trend_window) uptrend gate
with a deadband, dropping the oversold-threshold-cross entry/exit event
logic entirely (continuous exposure driven by REI's own magnitude/sign, not
a single -60-cross-then-rise trigger). This directly targets the prior
entry's parameter-sensitivity overfitting flag (a continuous dial is
typically much less sensitive to exact threshold placement than a binary
crossover) and ETH's narrow MDD near-miss (continuous position sizing
naturally reduces average exposure vs a binary 0/1 hold). First TD REI
continuous-sizing-dial strategy in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _compute_rei(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """TD REI (DeMark Range Expansion Index), unchanged formula from
    strategies/2026-09-16_td_rei_oversold_bounce_trend_gated.py."""
    hi2 = high.shift(2)
    lo2 = low.shift(2)
    lo5 = low.shift(5)
    lo6 = low.shift(6)
    hi5 = high.shift(5)
    hi6 = high.shift(6)
    cl7 = close.shift(7)
    cl8 = close.shift(8)

    cond_a = ((high >= lo5) | (high >= lo6)) & ((low <= hi5) | (low <= hi6))
    cond_b = ((hi2 >= cl7) | (hi2 >= cl8)) & ((lo2 <= cl7) | (lo2 <= cl8))
    condition = (cond_a | cond_b).fillna(False)

    value = (high - hi2 + low - lo2).where(condition, 0.0)
    absvalue = ((high - hi2).abs() + (low - lo2).abs()).where(condition, 0.0)

    sum_value = value.rolling(n).sum()
    sum_absvalue = absvalue.rolling(n).sum()
    rei = 100.0 * sum_value / sum_absvalue.replace(0.0, np.nan)
    return rei.fillna(0.0)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rei_period: int = 8,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    REI is already bounded [-100,100] -- rescaled to [-1,1] via /100, used
    directly (no z-score/tanh needed) as a sizing dial: exposure =
    clip(base_exposure + sensitivity*dial, 0, cap), gated to 0 whenever
    close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    trend_long = close > close.rolling(trend_window).mean()
    rei = _compute_rei(high, low, close, rei_period)
    dial = rei / 100.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rei_period: int = 8,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rei_period=rei_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
