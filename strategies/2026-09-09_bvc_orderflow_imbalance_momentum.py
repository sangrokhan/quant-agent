"""Strategy: Bulk-Volume-Classification (BVC) order-flow imbalance momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per quantmedia.io's "What is VPIN?" explainer (read this iteration) and the
underlying Easley/Lopez de Prado/O'Hara VPIN literature, Bulk Volume
Classification (BVC) infers buy- vs sell-initiated volume from the
standardized price change via a normal CDF, without needing tick data:
    buy_frac_t = Phi(return_t / sigma_t)
    Vb_t = volume_t * buy_frac_t ;  Vs_t = volume_t * (1 - buy_frac_t)
This repo only has daily OHLCV (no tick/order-flow feed), so true VPIN
(equal-*volume* buckets + literal |Vb-Vs| averaging) is infeasible per this
iteration's own research read -- but the BVC buy/sell-fraction primitive
itself only needs daily close-to-close returns + volume, both of which the
loaders provide. This strategy repurposes BVC as a *signed, volume-weighted
order-flow imbalance momentum* signal (a genuinely different construction
from OBV-divergence, which was tried and rejected in this repo as
2026-09-08-019 -- that used OBV's cumulative running total and looked for
price/OBV divergence; this instead computes a continuous, volume-weighted,
BVC-signed imbalance and thresholds its rolling average directly, with no
divergence/cumulative-sum logic):
    signed_imbalance_t = 2*buy_frac_t - 1                      (in [-1, 1])
    weighted_imbalance = sum(volume*signed_imbalance) / sum(volume)
                          over a trailing window (the closest daily-bar
                          analogue of a BVC "bucket average")
Hypothesis: persistent, volume-weighted net buying pressure (BVC-inferred)
sustained over the trailing window predicts near-term continuation --
i.e. an order-flow-based momentum signal, tested here on both equity and
crypto daily bars.

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
except Exception:  # pragma: no cover - fallback if scipy unavailable
    def _phi(x: pd.Series) -> pd.Series:
        # Logistic approximation to the standard normal CDF (close enough
        # for a [-1,1] imbalance signal; avoids a hard scipy dependency).
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
    signed_imbalance = 2 * buy_frac - 1  # in [-1, 1]

    num = (volume * signed_imbalance).rolling(imbalance_window).sum()
    den = volume.rolling(imbalance_window).sum().replace(0.0, np.nan)
    weighted_imbalance = (num / den).fillna(0.0)
    return weighted_imbalance


def generate_signals(
    price_df: pd.DataFrame,
    sigma_window: int = 20,
    imbalance_window: int = 10,
    entry_threshold: float = 0.08,
    exit_threshold: float = 0.0,
) -> pd.Series:
    """Long/flat {0,1} position: long while the trailing volume-weighted
    BVC order-flow imbalance stays above entry_threshold; exit when it
    drops back below exit_threshold (asymmetric hysteresis to avoid
    single-bar whipsaw)."""
    df = _prep(price_df)
    weighted_imbalance = _weighted_imbalance(df, sigma_window, imbalance_window)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        wi = weighted_imbalance.iloc[i]
        if in_position:
            if wi < exit_threshold:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if wi > entry_threshold:
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
