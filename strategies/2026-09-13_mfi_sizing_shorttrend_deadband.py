"""Strategy: SMA(short trend_window) trend-following gate with continuous
Money Flow Index (MFI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-089):
Money Flow Index (Gene Quong & Avrum Soudack), aka "volume-weighted RSI",
per chartschool.stockcharts.com (browser_exec fallback this iteration,
web_extract blocked -- DDGS search-only backend): TypicalPrice =
(High+Low+Close)/3, RawMoneyFlow = TypicalPrice*Volume, positive/negative
flow classified by whether TypicalPrice rose or fell period-over-period,
MoneyFlowRatio = sum(PositiveFlow, n) / sum(NegativeFlow, n), MFI = 100 -
100/(1+MoneyFlowRatio) -- bounded [0, 100] with a centerline at 50, exactly
matching the "bounded oscillator as continuous sizing dial" construction
already validated this cron trigger for %B/Aroon/Williams%R/CMO/UO/RVI/
StochRSI (2026-09-13-071/072/074/078/079/081/080). This repo has multiple
prior MFI entries, but all as binary threshold/divergence ENTRY signals --
none use MFI as a continuous sizing dial. Distinguishing feature vs. the
other 7 sizing-dial indicators tested this cron trigger: MFI is the ONLY
one that incorporates VOLUME (a "volume-weighted RSI"), so it captures a
structurally different signal (money flow / dollar volume pressure) rather
than pure price-range or price-momentum positioning. Hypothesis: exposure =
clip(base_exposure + mfi_sensitivity*((mfi-50)/50), 0, leverage_cap) within
an SMA(trend_window) uptrend, with an exposure-change deadband applied from
the start (per this cron trigger's learned lesson that un-smoothed bounded
oscillators need a deadband to survive transaction costs), and a SHORTENED
trend_window (this cron trigger's retrofit-family finding that trend_window
~30-50 beats the original default 200 for dual QQQ+SPY passes) used as the
starting default rather than re-discovering it from scratch.

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


def _mfi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Money Flow Index, bounded [0, 100]."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume

    tp_change = typical_price.diff()
    positive_flow = raw_money_flow.where(tp_change > 0, 0.0)
    negative_flow = raw_money_flow.where(tp_change < 0, 0.0)

    positive_sum = positive_flow.rolling(window).sum()
    negative_sum = negative_flow.rolling(window).sum()

    money_flow_ratio = positive_sum / negative_sum.replace(0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + money_flow_ratio))
    return mfi


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
    mfi_window: int = 14,
    base_exposure: float = 0.8,
    mfi_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    mfi = _mfi(df, window=mfi_window)

    raw_exposure = base_exposure + mfi_sensitivity * ((mfi - 50.0) / 50.0)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    mfi_window: int = 14,
    base_exposure: float = 0.8,
    mfi_sensitivity: float = 0.4,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        mfi_window=mfi_window,
        base_exposure=base_exposure,
        mfi_sensitivity=mfi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
