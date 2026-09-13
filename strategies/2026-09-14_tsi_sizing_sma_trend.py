"""Strategy: SMA(trend_window) directional gate with continuous True
Strength Index (TSI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-096):
True Strength Index (William Blau, Stocks & Commodities, Nov 1991; formula
per https://duckduckgo.com/html/?q=True+Strength+Index+TSI+formula (search
result summaries from nexusfi.com, trendsandbreakouts.com, and the
TA-Lib/ta-lib GitHub issue #360, all consistent): 1-bar price change (r)
double-smoothed with two chained EMAs (fast then slow) divided by the same
double-EMA chain applied to |r|, scaled x100: TSI = 100 * EMA(EMA(r, slow),
fast) / EMA(EMA(|r|, slow), fast). This is algebraically bounded to roughly
[-100, 100] (same ratio-of-smoothed-signed-vs-absolute construction as
RSI/CMO, just double-smoothed rather than single-smoothed), analogous to how
VZO/CHOP/ADX/DMI-diff/Vortex-diff-ratio were each turned into continuous
[0,leverage_cap] sizing dials earlier this cron trigger (all accepted
equity/rejected crypto).

This repo already has 7 prior TSI entries (2026-09-04-129, 2026-09-06-137,
2026-09-07-008, 2026-09-08-086, 2026-09-08-122, and 2+ others), ALL using TSI
as a binary threshold/crossover/signal-line ENTRY trigger -- all 7 rejected
(Sharpe/TC-survival failures). This iteration instead uses TSI as a
CONTINUOUS SIZING dial: within an existing SMA(trend_window) uptrend gate,
exposure scales up when TSI is strongly positive (momentum decisively
bullish) and scales down toward the base level as TSI fades toward/below
zero, rather than using TSI level/crossovers as a hard binary entry/exit
trigger. This directly tests whether TSI's repeated binary-signal rejections
were about the ENTRY-TRIGGER construction (as with VZO/ADX/CHOP/Vortex,
where binary triggers also failed before the sizing-dial reframing
succeeded) rather than TSI itself lacking predictive content.

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


def _tsi(close: pd.Series, fast: int = 13, slow: int = 25) -> pd.Series:
    """TSI = 100 * EMA(EMA(mom, slow), fast) / EMA(EMA(|mom|, slow), fast).

    Blau's original naming convention pairs "slow" with the first (longer)
    smoothing pass and "fast" with the second (shorter) pass; here `slow`
    is the first EMA span and `fast` the second, matching common defaults
    (25 then 13). Bounded ~[-100, 100] by construction (ratio of a smoothed
    signed quantity to its smoothed absolute value, scaled by 100).
    """
    mom = close.diff()
    smoothed1 = mom.ewm(span=slow, adjust=False).mean()
    smoothed2 = smoothed1.ewm(span=fast, adjust=False).mean()

    abs_smoothed1 = mom.abs().ewm(span=slow, adjust=False).mean()
    abs_smoothed2 = abs_smoothed1.ewm(span=fast, adjust=False).mean()

    denom = abs_smoothed2.replace(0, np.nan)
    tsi = 100.0 * smoothed2 / denom
    return tsi.clip(lower=-100.0, upper=100.0)


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
    tsi_fast: int = 13,
    tsi_slow: int = 25,
    base_exposure: float = 0.5,
    tsi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tsi = _tsi(close, fast=tsi_fast, slow=tsi_slow)
    tsi_norm = tsi / 100.0  # rescale to roughly [-1, 1]

    raw_exposure = base_exposure + tsi_sensitivity * tsi_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tsi_fast: int = 13,
    tsi_slow: int = 25,
    base_exposure: float = 0.5,
    tsi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        tsi_fast=tsi_fast,
        tsi_slow=tsi_slow,
        base_exposure=base_exposure,
        tsi_sensitivity=tsi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
