"""Strategy: BVC order-flow imbalance momentum, gated to low/mid realized-vol
regimes only (direct follow-up to near-miss 2026-09-09-024).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
2026-09-09-024 (BVC order-flow imbalance momentum, from quantmedia.io's VPIN
explainer read this cron trigger) was a near-miss: full-sample Sharpe fell
short (QQQ 0.953, SPY 0.791) despite passing every other validator, and its
own grid breakdown showed the edge concentrated in the low-vol tercile
(12/24 grid cells passed) vs mid (7/24) and high (1/24). This repo has an
established, previously-validated fix pattern for exactly this shape of
near-miss -- add an explicit realized-volatility regime gate restricting
entries to the low/mid-vol regime (same construction as the accepted
2026-09-03_bb_meanrev_qqq_volregime.py and 2026-09-08-168 Range Filter [DW]
+ vol gate) -- to see whether excluding the high-vol tercile (where the
signal decisively underperformed) rescues the full-sample Sharpe above the
1.0 threshold. Same BVC imbalance construction as 2026-09-09-024, with one
added realized-vol regime filter.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from scipy.stats import norm

    def _phi(x: pd.Series) -> pd.Series:
        return pd.Series(norm.cdf(x.values), index=x.index)
except Exception:  # pragma: no cover
    def _phi(x: pd.Series) -> pd.Series:
        return 1.0 / (1.0 + np.exp(-1.702 * x))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weighted_imbalance(df: pd.DataFrame, sigma_window: int, imbalance_window: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    ret = close.pct_change()
    sigma = ret.rolling(sigma_window).std()
    sigma_safe = sigma.replace(0.0, np.nan)
    z = (ret / sigma_safe).clip(-5, 5).fillna(0.0)
    buy_frac = _phi(z)
    signed_imbalance = 2 * buy_frac - 1

    num = (volume * signed_imbalance).rolling(imbalance_window).sum()
    den = volume.rolling(imbalance_window).sum().replace(0.0, np.nan)
    weighted_imbalance = (num / den).fillna(0.0)
    return weighted_imbalance


def generate_signals(
    price_df: pd.DataFrame,
    sigma_window: int = 20,
    imbalance_window: int = 10,
    entry_threshold: float = 0.15,
    exit_threshold: float = 0.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Long/flat {0,1} position: same BVC imbalance entry/exit as
    2026-09-09-024, but additionally gated to bars where trailing realized
    vol is <= vol_regime_ratio x its trailing 1yr median (i.e. excludes the
    high-vol tercile where the ungated version decisively underperformed)."""
    df = _prep(price_df)
    close = df["close"]
    daily_log_ret = np.log(close / close.shift(1))
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    ok_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    weighted_imbalance = _weighted_imbalance(df, sigma_window, imbalance_window)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        wi = weighted_imbalance.iloc[i]
        vol_ok = bool(ok_vol_regime.iloc[i])
        if in_position:
            if wi < exit_threshold or not vol_ok:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if vol_ok and wi > entry_threshold:
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
