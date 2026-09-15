"""Strategy: Overnight-only hold (prior close -> next open, flat intraday),
gated by 12-1 skip-month momentum AND a realized-volatility regime filter.

Hypothesis (knowledge_base id 2026-09-15-109):
Direct fix for this same cron trigger's near-miss/rejection 2026-09-16-108
(overnight-hold + 12-1 momentum gate: QQQ MDD 0.274 near-miss, SPY Sharpe
0.781 + MDD 0.294 both fail; grid decisively failed in the high-vol tercile
across every param/asset combo -- 0/32 high-vol passes). Per that entry's
own follow-up note, this iteration adds an explicit realized-volatility
regime gate (same construction as this repo's accepted BB mean-reversion
2026-09-03-001: current 20d realized vol vs trailing 252d median, flat
whenever in the high-vol regime) on top of the unchanged 12-1 momentum
overnight-hold logic, to see if excluding high-vol nights rescues the QQQ
MDD near-miss and SPY's shortfall the same way 2026-09-08-053's SMA trend
filter improved on the plain unconditional overnight hold 2026-09-03-007.

No new external research this sub-iteration -- source for the underlying
overnight+momentum mechanism remains
https://alphaarchitect.com/overnight-momentum-vs-intraday-momentum/ (Lou,
Polk, Skouras); the vol-regime-gate construction is this repo's own
established pattern, not a new source.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position, held
    only overnight).
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


def _momentum_12_1(close: pd.Series, lookback_months: int, skip_months: int, bars_per_month: int) -> pd.Series:
    lookback_bars = lookback_months * bars_per_month
    skip_bars = skip_months * bars_per_month
    far = close.shift(lookback_bars)
    near = close.shift(skip_bars)
    return (near / far) - 1.0


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std()
    trailing_median = realized_vol.rolling(vol_lookback, min_periods=max(30, vol_lookback // 4)).median()
    is_low_vol = realized_vol <= (vol_regime_ratio * trailing_median)
    return is_low_vol.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_months: int = 12,
    skip_months: int = 1,
    bars_per_month: int = 21,
    mom_threshold: float = 0.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a 0/1 series: 1 means "hold overnight tonight", gated by
    positive 12-1 skip-month momentum AND a low/normal realized-vol regime.
    """
    df = _prep(price_df)
    close = df["close"]

    mom = _momentum_12_1(close, lookback_months, skip_months, bars_per_month)
    mom_gate = (mom > mom_threshold).fillna(False)

    vol_gate = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    hold_overnight = (mom_gate & vol_gate).astype(float)
    return hold_overnight


def generate_returns(
    price_df: pd.DataFrame,
    lookback_months: int = 12,
    skip_months: int = 1,
    bars_per_month: int = 21,
    mom_threshold: float = 0.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: only close(t)->open(t+1) overnight return is
    captured, only when both the momentum gate and vol-regime gate agree.
    """
    df = _prep(price_df)
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    overnight_ret = (open_.shift(-1) / close) - 1.0
    overnight_ret = overnight_ret.fillna(0.0)

    gate = generate_signals(
        price_df,
        lookback_months=lookback_months,
        skip_months=skip_months,
        bars_per_month=bars_per_month,
        mom_threshold=mom_threshold,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )

    strat_ret = gate * overnight_ret
    strat_ret = strat_ret.shift(1).fillna(0.0)
    return strat_ret
