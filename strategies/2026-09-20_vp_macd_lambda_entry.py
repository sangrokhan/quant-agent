"""Strategy: Volume-Price-Adjusted MACD (VP-MACD) with lambda-adjusted entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-063):
Per Lin, Lin, Zhang, Zheng & Wang (2026), "A Volume-Price-Adjusted MACD
Trading Strategy with Sensitivity Calibration for U.S. Equity Indices"
(arXiv:2604.26063, https://arxiv.org/abs/2604.26063), the VP-MACD
framework replaces the conventional closing-price input to MACD with an
adjusted price series P*_t that jointly weights volume intensity,
intraday volatility, and candlestick body ratio:

    P*_t = sum_{i=t-N}^{t-1} (P_i * Volume_i * sigma_i * r_i)
           / sum_{i=t-N}^{t-1} Volume_i

where sigma_i = std(High_i - Low_i) / Close_i (rolling-window-normalized
range volatility) and r_i = |Close_i - Open_i| / (High_i - Low_i) (the
candlestick body ratio, capturing directional conviction vs. wick-heavy
indecision). VP-MACD_t = EMA12(P*_t) - EMA26(P*_t), Signal_t =
EMA9(VP-MACD_t). The paper's own key innovation is a sensitivity
parameter lambda in (0.8, 1) that RELAXES the crossover entry condition:
buy when VP-MACD_t > lambda * Signal_t (rather than waiting for a full
crossover), enabling earlier participation while lambda>0.8 prevents
over-relaxing into noise. The paper reports this VP-MACD + lambda-relaxed
entry outperforms baseline MACD on SPX/NDX/DJIA out-of-sample (2023-Feb
2026) on profitability, risk-adjusted return, and downside control, with
fewer/more selective trades.

First strategy in this repo using this specific volume x volatility x
candlestick-body-weighted price series as the MACD input -- distinct
from the already-tested Volume-Weighted MACD (VW-MACD, 2026-09-18-061,
which only volume-weights via VWMA, with no volatility/body-ratio
component) and from all other MACD variants in this repo (zeroline,
histogram-divergence, RSI-dual-confirmation, etc.), none of which
construct an adjusted *price series* feeding into standard EMA MACD.

We use volume_window as the rolling N in the paper's Eq. 8-10 (paper
doesn't disclose N explicitly beyond "rolling calculation" over a
lookback window; treated as a tunable grid parameter here), and expose
lambda_sensitivity directly per the paper's own (0.8, 1) calibration
range. Adapted to a long/flat contract (source is long/short on index
futures; we drop shorts per this repo's standing convention for singular
trend-following crossovers) -- long when VP-MACD > lambda*Signal, flat
otherwise.

Signal logic
------------
- sigma_i = rolling_std(High-Low, vol_window) / Close  [per Eq. 9,
  "STD(High-Low)" interpreted as a rolling standard deviation of the
  daily range over vol_window, normalized by close].
- r_i = |Close-Open| / (High-Low), with (High-Low)==0 guarded to avoid
  div-by-zero.
- adjusted_price_t = rolling volume-weighted average of (Close*sigma*r)
  over `volume_window` trading days, weighted by Volume (Eq. 8).
- vp_macd = EMA12(adjusted_price) - EMA26(adjusted_price).
- signal = EMA9(vp_macd).
- Long (position=1) when vp_macd > lambda_sensitivity * signal; flat
  otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _vp_macd_inputs(df: pd.DataFrame, volume_window: int) -> pd.Series:
    """Build the volume-price-adjusted price series P*_t per Eq. 8-10."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    rng = (high - low).replace(0, np.nan)
    sigma = rng.rolling(volume_window).std() / close
    r = (close - open_).abs() / rng
    r = r.fillna(0.0)
    sigma = sigma.fillna(0.0)

    weighted_component = close * sigma * r * volume
    numerator = weighted_component.rolling(volume_window).sum()
    denominator = volume.rolling(volume_window).sum().replace(0, np.nan)
    adjusted_price = (numerator / denominator).fillna(close)
    return adjusted_price


def generate_signals(
    price_df: pd.DataFrame,
    volume_window: int = 20,
    lambda_sensitivity: float = 0.9,
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``trend_window`` is an OPTIONAL defensive addition beyond the source
    paper's bare lambda-relaxed crossover (paper's own rule has no trend
    filter): when > 0, gate long entries on close > SMA(trend_window),
    the same defensive pattern already validated for other crossover-prone
    indicators in this repo (KAMA/LSMA/PMA/One Euro Filter). Set to 0 to
    reproduce the paper's rule exactly (no trend gate).
    """
    df = _prep(price_df)
    close = df["close"]
    adjusted_price = _vp_macd_inputs(df, volume_window=volume_window)

    ema12 = adjusted_price.ewm(span=12, adjust=False).mean()
    ema26 = adjusted_price.ewm(span=26, adjust=False).mean()
    vp_macd = ema12 - ema26
    signal = vp_macd.ewm(span=9, adjust=False).mean()

    long_condition = (vp_macd > lambda_sensitivity * signal).fillna(False)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_up = (close > sma).fillna(False)
        long_condition = long_condition & trend_up

    position = long_condition.astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    volume_window: int = 20,
    lambda_sensitivity: float = 0.9,
    trend_window: int = 0,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        volume_window=volume_window,
        lambda_sensitivity=lambda_sensitivity,
        trend_window=trend_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
