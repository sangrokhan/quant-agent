"""Strategy: Constance Brown CMB Composite Index MA-crossover + realized-vol
regime filter, long-only. Direct fix for QQQ near-miss.

Hypothesis (knowledge_base id 2026-09-15-113):
Direct fix for this same cron trigger's prior entry 2026-09-16-112
(Constance Brown CMB Composite Index MA-crossover: SPY accepted Sharpe
1.261/MDD 0.166, QQQ near-miss Sharpe 0.895-0.921/MDD 0.213-0.242 across
every config tried including a dedicated 61-combo QQQ-specific parameter
search). Per that entry's implied follow-up (this repo's established
2026-09-03-001 pattern), this iteration adds an explicit realized-vol
regime filter (20d realized vol vs trailing 252d median, flat whenever in
the high-vol regime) on top of the unchanged Composite Index MA-crossover
mechanics, to see if excluding high-vol whipsaw periods rescues QQQ. No
new external research this sub-iteration -- source for the underlying
Composite Index formula remains
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/cmb-composite-index
(Constance Brown); the vol-regime-gate construction is this repo's own
established pattern, not a new source.

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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _composite_index(
    close: pd.Series,
    rsi_period: int,
    roc_period: int,
    mom_rsi_period: int,
    mom_sma_period: int,
) -> pd.Series:
    rsi_main = _rsi(close, rsi_period)
    rsi_chg = rsi_main.diff(roc_period)

    rsi_short = _rsi(close, mom_rsi_period)
    rsi_mom = rsi_short.rolling(mom_sma_period).mean()

    composite = rsi_chg + rsi_mom
    return composite


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std()
    trailing_median = realized_vol.rolling(vol_lookback, min_periods=max(30, vol_lookback // 4)).median()
    is_low_vol = realized_vol <= (vol_regime_ratio * trailing_median)
    return is_low_vol.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    roc_period: int = 9,
    mom_rsi_period: int = 3,
    mom_sma_period: int = 3,
    fast_ma_period: int = 10,
    slow_ma_period: int = 45,
    max_hold_days: int = 30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Long-only: enter when the Composite Index Line crosses above BOTH
    its fast and slow SMAs AND we are in a low/normal realized-vol regime;
    exit when either the crossover condition or the vol regime breaks, or
    after max_hold_days.
    """
    df = _prep(price_df)
    close = df["close"]

    composite = _composite_index(close, rsi_period, roc_period, mom_rsi_period, mom_sma_period)
    fast_ma = composite.rolling(fast_ma_period).mean()
    slow_ma = composite.rolling(slow_ma_period).mean()

    crossover_long = (composite > fast_ma) & (composite > slow_ma)
    vol_gate = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)
    long_condition = (crossover_long & vol_gate).fillna(False)

    position = pd.Series(0.0, index=close.index)
    vals = long_condition.to_numpy()
    pos = position.to_numpy().copy()
    in_position = False
    bars_held = 0
    for i in range(len(vals)):
        if in_position:
            bars_held += 1
            if not vals[i] or bars_held >= max_hold_days:
                in_position = False
                bars_held = 0
                pos[i] = 0.0
            else:
                pos[i] = 1.0
        else:
            if vals[i]:
                in_position = True
                bars_held = 0
                pos[i] = 1.0
            else:
                pos[i] = 0.0
    return pd.Series(pos, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    roc_period: int = 9,
    mom_rsi_period: int = 3,
    mom_sma_period: int = 3,
    fast_ma_period: int = 10,
    slow_ma_period: int = 45,
    max_hold_days: int = 30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        roc_period=roc_period,
        mom_rsi_period=mom_rsi_period,
        mom_sma_period=mom_sma_period,
        fast_ma_period=fast_ma_period,
        slow_ma_period=slow_ma_period,
        max_hold_days=max_hold_days,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
