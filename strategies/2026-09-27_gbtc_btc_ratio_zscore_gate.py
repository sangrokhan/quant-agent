"""Strategy: GBTC/BTC ratio z-score regime gate on a primary asset's
SMA trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Before its January 2024 conversion to a spot ETF, GBTC (Grayscale Bitcoin
Trust) traded as a closed-end fund whose market price could deviate
substantially from its underlying BTC NAV (premium during institutional
demand/bull euphoria, deep discount during capitulation/liquidity stress --
e.g. the 2022 FTX-collapse discount exceeded -40%). Per general market
knowledge of the GBTC premium/discount phenomenon (a widely-documented
sentiment gauge cited across CryptoQuant/Bitcoin-Mastery/GlobalCoinGuide
sources found this iteration, though the exact NAV feed itself is
proprietary and feasibility-blocked, as recorded in a prior rejected
iteration 2026-09-27-074) -- this strategy instead uses the DIRECTLY
LOADABLE GBTC market price divided by BTC/USDT spot price as a proxy ratio,
rolling z-scored (which normalizes away the fixed BTC-per-share conversion
factor baked into the ratio's level, leaving only the ratio's relative
DEVIATION from its own trailing mean/std -- i.e. the premium/discount
SIGNAL, not its absolute magnitude). This sidesteps the specific NAV-feed
feasibility blocker recorded previously by using two data sources this
repo's loaders ALREADY expose (yfinance GBTC, ccxt BTC/USDT), rather than
requiring a dedicated GBTC-NAV/flow API.

Regime gate: a rolling z-score of the GBTC/BTC ratio strongly negative
(z <= low_z_threshold, i.e. an unusually deep "discount" episode relative
to its own trailing history) signals crypto-market liquidity stress /
capitulation -- risk OFF, flatten regardless of the base trend signal. A
z-score at/above a neutral band means normal conditions -- trade the base
SMA(trend_window) trend-following signal on the primary asset as usual.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series

Note: price_df is the PRIMARY asset's OHLCV (as usual); this module loads
GBTC and BTC/USDT internally via data/loaders.py to compute the ratio,
following the established internal-ratio-denominator-load pattern already
used elsewhere in this repo (e.g. the Gold/Silver-Ratio RSI strategy).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gbtc_btc_zscore(index: pd.DatetimeIndex, zscore_window: int) -> pd.Series:
    from loaders import load_equity, load_crypto

    start = index.min() - pd.Timedelta(days=zscore_window * 3 + 30)
    end = index.max() + pd.Timedelta(days=5)

    gbtc = load_equity("GBTC", start.to_pydatetime(), end.to_pydatetime(), interval="1d")
    btc = load_crypto("BTC/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d")

    gbtc = _prep(gbtc)["close"].rename("gbtc")
    btc = _prep(btc)["close"].rename("btc")

    merged = pd.concat([gbtc, btc], axis=1).dropna()
    ratio = merged["gbtc"] / merged["btc"]

    roll_mean = ratio.rolling(zscore_window).mean()
    roll_std = ratio.rolling(zscore_window).std()
    zscore = (ratio - roll_mean) / roll_std.replace(0, float("nan"))

    zscore = zscore.reindex(index, method="ffill")
    return zscore


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    low_z_threshold: float = -1.5,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    min_hold_days: once a position changes (enter or exit), hold it for at
        least this many bars before allowing another flip -- reduces
        whipsaw trade frequency from the SMA trend signal's own noise,
        addressing the transaction-cost drag from high turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    base_trend = close > sma

    zscore = _gbtc_btc_zscore(close.index, zscore_window)
    risk_off = zscore <= low_z_threshold

    raw_position = (base_trend & (~risk_off.fillna(False))).astype(int)

    n = len(raw_position)
    raw_v = raw_position.values
    state = raw_v.copy()
    last_change = 0
    for i in range(1, n):
        if state[i] != state[i - 1]:
            if (i - last_change) < min_hold_days:
                state[i] = state[i - 1]
            else:
                last_change = i

    position = pd.Series(state, index=close.index).astype(bool)
    signal = position.shift(1).fillna(False).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    low_z_threshold: float = -1.5,
    min_hold_days: int = 5,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        zscore_window=zscore_window,
        low_z_threshold=low_z_threshold,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
