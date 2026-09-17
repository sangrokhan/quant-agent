"""Strategy: Apirine Rate Of Change With Bands (ROCWB) reversal-confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-160):
Vitali Apirine's Traders' Tips article (TASC Mar 2021, "Rate Of Change With
Bands", source: Traders.com Mar 2021 Traders' Tips, TradeStation
EasyLanguage code read this iteration) builds volatility-adaptive bands
around a smoothed rate-of-change (MA-ROC), where the band width is the RMS
(root-mean-square) of the RAW rate-of-change series (NOT a standard
deviation of the ROC around its own mean -- distinct from every prior
plain-ROC/z-score-ROC strategy in this repo, which normalize by mean and
stdev). Trading rule: within a long-term uptrend (close > EMA200), MA-ROC
crossing UP through the LowerBand marks a momentum-exhaustion recovery (the
downside momentum spike is fading) -- a reversal-confirmation long entry,
not a simple oversold-dip-buy. Exit when MA-ROC crosses DOWN through the
UpperBand (momentum getting overextended to the upside, or losing the
recovery). This dual condition (trend regime gate + band-crossing direction
tied to trend direction) with RMS-based (not stdev-based) bands is a novel
combination in this repo.

Formula (per source)
---------------------
- RateOfChg = ROC(Close, periods1) = (Close - Close[periods1]) / Close[periods1] * 100
- ROCDev = sqrt(rolling_mean(RateOfChg^2, periods3))  (RMS, not stdev)
- MaRateOfChg = EMA(RateOfChg, periods2)
- UpperBand = ROCDev * num_dev_up, LowerBand = ROCDev * num_dev_dn (num_dev_dn
  negative, e.g. -1)
- EMA(Close, ema_len) = long-term trend filter.

Signal logic (long-only adaptation; original also shorts in downtrend)
------------------------------------------------------------------------
- Entry (long, only when Close > EMA(ema_len)): MaRateOfChg crosses above
  LowerBand.
- Exit: MaRateOfChg crosses below UpperBand, OR close falls below EMA
  (trend regime flip), OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    periods1: int = 12,
    periods2: int = 3,
    periods3: int = 12,
    num_dev_up: float = 1.0,
    num_dev_dn: float = -1.0,
    ema_len: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = close.pct_change(periods1) * 100
    roc_dev = np.sqrt((roc ** 2).rolling(periods3).mean())
    ma_roc = roc.ewm(span=periods2, adjust=False).mean()

    upper_band = roc_dev * num_dev_up
    lower_band = roc_dev * num_dev_dn

    ema = close.ewm(span=ema_len, adjust=False).mean()
    up_trend = close > ema

    entry = (ma_roc.shift(1) <= lower_band.shift(1)) & (ma_roc > lower_band) & up_trend
    exit_signal = ((ma_roc.shift(1) >= upper_band.shift(1)) & (ma_roc < upper_band)) | (~up_trend)

    warmup = max(periods1, periods2, periods3, ema_len)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
