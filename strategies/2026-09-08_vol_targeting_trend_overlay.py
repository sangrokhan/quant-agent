"""Strategy: Inverse-volatility position-sizing overlay on a simple trend signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-165):
Per https://realbacktesting.com/academy/volatility-targeting-explained.html
(summarizing Moreira-Muir "Volatility-Managed Portfolios" and Harvey et al.'s
volatility-targeting study), scaling a position's notional exposure inversely
to its trailing realized volatility (raw_exposure = target_vol /
estimated_vol, capped by a leverage ceiling) smooths realized risk through
time and, per the cited academic literature, tends to raise risk-adjusted
returns most for equities/credit-like risk assets (the source explicitly
flags weaker/inconsistent benefit for bonds/currencies/commodities). This is
tested here as an OVERLAY on top of a plain SMA-trend long/flat signal
(distinct from every other trend/momentum strategy already in this repo,
which all use fixed 0/1 position sizing) -- i.e. we isolate whether the
position-SIZING mechanism itself (not the entry timing) improves risk-adjusted
performance versus the same trend signal traded at fixed full size.

Signal logic
------------
- Trend gate: close > SMA(trend_window) -> want to be long, else flat
  (identical directional signal to many existing strategies in this repo, so
  any edge/rejection here isolates the SIZING mechanism, not entry timing).
- When the trend gate is long, size the position as
  exposure = min(target_vol / realized_vol, leverage_cap), using ONLY
  trailing (already-completed, non-look-ahead) realized volatility of daily
  log returns over vol_window days, annualized.
- realized_vol and the SMA trend gate are both computed on data available
  strictly before the trading day (shifted by 1 bar in generate_returns, same
  convention as every other strategy in this repo) to avoid look-ahead bias
  (the source's own explicitly flagged risk).
- Exposure floor of 0 when flat; no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        Here generate_signals returns the *continuous* target exposure
        series in [0, leverage_cap] (not strictly {0,1}) since the sizing
        mechanism itself is the object of the hypothesis; still 0 whenever
        the trend gate is flat.
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


def _realized_vol(close: pd.Series, vol_window: int) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    return daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap]."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    realized_vol = _realized_vol(close, vol_window)
    # Avoid divide-by-zero / extreme blow-ups on near-zero vol readings.
    safe_vol = realized_vol.clip(lower=1e-4)
    raw_exposure = (target_vol / safe_vol).clip(upper=leverage_cap)

    exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    exposure = exposure.fillna(0.0).clip(lower=0.0, upper=leverage_cap)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift exposure by 1 day: yesterday's signal/sizing determines today's
    # return exposure (avoid look-ahead bias -- can't trade on today's own
    # close, and can't size using today's own not-yet-fully-observed vol).
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
