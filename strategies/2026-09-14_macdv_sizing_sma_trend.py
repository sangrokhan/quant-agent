"""Strategy: SMA(trend_window) directional gate with continuous MACD-V
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
MACD-V (Alex Spiroglou, 2022, volatility-normalized MACD):
MACD-V = [(EMA12-EMA26)/ATR(26)] * 100, Signal = EMA9(MACD-V). Per
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
(visited this iteration via browser_exec Google SERP fallback -- web_search
DDGS returned generic/unrelated indicator results, not this exact page).

This repo has 2 prior MACD-V entries, BOTH binary threshold/crossover rules
on the (approximately) bounded momentum-stage zones the source itself
defines ("Rebounding" -100..80, accepted equity-only 2026-09-06-094;
"Rallying" 50..150, rejected 2026-09-12-155, Sharpe near-miss + crypto
decisive reject). Neither used MACD-V's own already-roughly-bounded value
(source states typical range is -150..+150 in practice, occasionally wider)
as a CONTINUOUS SIZING dial -- this cron trigger's validated pattern for
other momentum/volume oscillators (CMO, RVI, PSY, GAPO, etc.) that avoids
the threshold/crossover pass-fraction fragility. This iteration applies that
pattern here for the first time: clip MACD-V to [-cap, +cap] and rescale to
[-1, +1] as a sizing dial within the SMA(trend_window) uptrend gate,
addressing 2026-09-12-155's rejection mode (edge concentrated narrowly in
one momentum-stage band with pass_fraction 0.176) by using the full
continuous signal instead of a narrow threshold zone.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    return tr.ewm(alpha=1.0 / window, adjust=False).mean()


def _macdv(close: pd.Series, atr: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    return (macd / atr.replace(0.0, np.nan)) * 100.0


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
    atr_window: int = 26,
    macdv_cap: float = 150.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    MACD-V is clipped to [-macdv_cap, +macdv_cap] (source's own typical
    practical range) then rescaled to [-1,+1] and used directly as a sizing
    dial, gated to zero exposure outside the SMA(trend_window) uptrend.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    atr = _atr(df, atr_window)
    macdv = _macdv(close, atr)
    macdv_clipped = macdv.clip(lower=-macdv_cap, upper=macdv_cap)
    macdv_centered = macdv_clipped / macdv_cap  # rescale -> [-1,+1]

    raw_exposure = base_exposure + sensitivity * macdv_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    atr_window: int = 26,
    macdv_cap: float = 150.0,
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
        atr_window=atr_window,
        macdv_cap=macdv_cap,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
