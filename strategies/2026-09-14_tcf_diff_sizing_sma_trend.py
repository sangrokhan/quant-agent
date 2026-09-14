"""Strategy: SMA(trend_window) directional gate with continuous Trend
Continuation Factor (TCF, M.H. Pee) diff sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Trend Continuation Factor (TCF, M.H. Pee, TASC Mar 2001), per ProRealCode's
disclosed PRT source (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
strategies/2026-09-08_tcf_crossover_pee.py, no fresh web fetch needed this
sub-step):
    r = ROC(1, close)                      -- 1-bar difference
    pc = max(r, 0); nc = max(-r, 0)
    ncf, pcf = running cumulative sums of nc, pc, each RESET to 0
               whenever nc==0 / pc==0 respectively
    TCF+ = SUM(pc, sumperiod) - SUM(ncf, sumperiod)
    TCF- = SUM(nc, sumperiod) - SUM(pcf, sumperiod)
This repo's only prior TCF entry (2026-09-08-027) used the TCF+/TCF-
CROSSOVER as a binary ENTRY trigger (accepted QQQ-only, SPY near-miss,
crypto rejected decisively). This iteration instead reframes the signed
diff (TCF+ - TCF-) as a CONTINUOUS SIZING dial: rolling z-scored and
tanh-squashed to [-1,+1] (since the raw diff is unbounded, unlike a
naturally-bounded oscillator), within an SMA(trend_window) uptrend gate --
the same "unbounded diff -> z-score -> tanh" reframing pattern already
used for Vortex-diff-ratio/DMI-diff/RWI-diff elsewhere in this repo, and
distinct from the "already-bounded, direct rescale" pattern used for
Firefly/Elegant/VoRSI earlier this same cron trigger. Economic rationale:
TCF+/TCF- track the relative accumulated "pressure" of up-moves vs
down-moves (with a reset-on-sign-flip mechanic that discounts stale runs);
a large positive (TCF+ - TCF-) signals sustained bullish pressure building
relative to bearish pressure, warranting larger exposure within an
established uptrend, while a near-zero diff signals the two forces are
roughly balanced (low conviction) even while price stays nominally above
the SMA trend filter. First TCF continuous-sizing variant.

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


def _tcf(close: pd.Series, sumperiod: int) -> tuple[pd.Series, pd.Series]:
    """Trend Continuation Factor (TCF+, TCF-), reused exactly per
    ProRealCode's disclosed PRT source (M.H. Pee, TASC Mar 2001)."""
    r = close.diff()
    pc = r.clip(lower=0.0).fillna(0.0)
    nc = (-r).clip(lower=0.0).fillna(0.0)

    n = len(close)
    ncf = np.zeros(n)
    pcf = np.zeros(n)
    nc_vals = nc.to_numpy()
    pc_vals = pc.to_numpy()
    for i in range(n):
        if nc_vals[i] == 0.0:
            ncf[i] = 0.0
        else:
            ncf[i] = (ncf[i - 1] if i > 0 else 0.0) + nc_vals[i]
        if pc_vals[i] == 0.0:
            pcf[i] = 0.0
        else:
            pcf[i] = (pcf[i - 1] if i > 0 else 0.0) + pc_vals[i]

    ncf_s = pd.Series(ncf, index=close.index)
    pcf_s = pd.Series(pcf, index=close.index)

    tcf_plus = pc.rolling(sumperiod).sum() - ncf_s.rolling(sumperiod).sum()
    tcf_minus = nc.rolling(sumperiod).sum() - pcf_s.rolling(sumperiod).sum()
    return tcf_plus, tcf_minus


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
    sumperiod: int = 35,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Signed diff (TCF+ - TCF-) is rolling-z-scored over `zscore_window`
    bars and tanh-squashed to [-1,+1] before use as a sizing dial, within
    an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    tcf_plus, tcf_minus = _tcf(close, sumperiod)
    diff = (tcf_plus - tcf_minus).fillna(0.0)

    roll_mean = diff.rolling(zscore_window).mean()
    roll_std = diff.rolling(zscore_window).std()
    zscore = (diff - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    sumperiod: int = 35,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        sumperiod=sumperiod,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
