"""Strategy: Dual crypto-trust-discount consensus gate (GBTC/BTC AND ETHE/ETH
ratio z-scores must BOTH indicate stress) on a primary asset's SMA
trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
This cron trigger's earlier iteration (2026-09-27-095) used the GBTC/BTC
market-price ratio's rolling z-score alone as a single risk-off proxy gate
(accepted QQQ+SPY). Grayscale's Ethereum Trust (ETHE, now converted to a
spot ETF like GBTC, per companiesmarketcap.com/YCharts confirming its
premium/discount is now near-zero post-conversion but historically
deviated substantially, mirroring GBTC's own pre-2024 conversion history)
provides an INDEPENDENT second crypto-trust discount signal. This strategy
tests whether requiring BOTH proxies to simultaneously signal stress (an
AND-gate consensus across two independent trust vehicles tracking two
different underlying assets, BTC and ETH) produces a more reliable
risk-off signal than either alone -- the economic rationale being that a
genuine market-wide crypto liquidity/capitulation event should show up in
BOTH trusts' relative pricing simultaneously, filtering out idiosyncratic
single-trust noise (e.g. a single large redemption/creation event specific
to one trust that doesn't reflect broader market stress).

Distinct from 2026-09-27-095 (single-ratio z-score gate) via the AND-gate
CONSENSUS mechanic across two independent cross-asset ratios, rather than
one.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _ratio_zscore(a: pd.Series, b: pd.Series, zscore_window: int) -> pd.Series:
    merged = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    ratio = merged["a"] / merged["b"]
    roll_mean = ratio.rolling(zscore_window).mean()
    roll_std = ratio.rolling(zscore_window).std()
    zscore = (ratio - roll_mean) / roll_std.replace(0, float("nan"))
    return zscore


def _dual_trust_stress(index: pd.DatetimeIndex, zscore_window: int, low_z_threshold: float) -> pd.Series:
    from loaders import load_equity, load_crypto

    start = index.min() - pd.Timedelta(days=zscore_window * 3 + 30)
    end = index.max() + pd.Timedelta(days=5)

    gbtc = _prep(load_equity("GBTC", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    btc = _prep(load_crypto("BTC/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    ethe = _prep(load_equity("ETHE", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    eth = _prep(load_crypto("ETH/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]

    gbtc_z = _ratio_zscore(gbtc, btc, zscore_window)
    ethe_z = _ratio_zscore(ethe, eth, zscore_window)

    gbtc_z = gbtc_z.reindex(index, method="ffill")
    ethe_z = ethe_z.reindex(index, method="ffill")

    stress = (gbtc_z <= low_z_threshold) & (ethe_z <= low_z_threshold)
    return stress


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    low_z_threshold: float = -1.0,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    base_trend = close > sma

    stress = _dual_trust_stress(close.index, zscore_window, low_z_threshold)

    raw_position = (base_trend & (~stress.fillna(False))).astype(int)

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
    low_z_threshold: float = -1.0,
    min_hold_days: int = 10,
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
