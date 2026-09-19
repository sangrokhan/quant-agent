"""Strategy: MARA/BTC leveraged-beta-overshoot z-score mean-reversion gate
on BTC (and equity falsification legs).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per Yahoo Finance ("MARA's beta of 5 ... amplif[ies] both crypto and tech-
tape moves"), Tickeron, and Perplexity Finance explainers (Google SERP
snippets, read via browser_exec this iteration -- initial web_search
returned normal results for the query, no fallback needed), MARA (Marathon
Digital/Marathon Holdings, a bitcoin-mining company) trades as a
high-beta, LEVERAGED proxy for bitcoin -- its stock price historically
amplifies BTC's moves in both directions (roughly 5x beta per the cited
Yahoo Finance piece), driven by (1) operating leverage on mining margins,
(2) balance-sheet BTC holdings, and (3) speculative equity-market flows
into "crypto plays."

This is architecturally distinct from the already-tested MSTR/BTC mNAV-
LEVEL trend-following gate (2026-09-20-040/041, which treats the ratio's
LEVEL vs its own SMA as a risk-on/risk-off TREND regime signal) and the
BITO/BTC roll-decay-RATE-OF-CHANGE gate (2026-09-20-042, rejected). Here,
the economic thesis is MEAN-REVERSION of the leverage relationship itself:
when the MARA/BTC ratio's z-score becomes extreme (MARA has overshot BTC's
own move by an unusually large multiple, positive OR negative, relative to
its own recent history), the amplified move is hypothesized to partially
unwind (beta-adjusted overreaction), creating a short-term BTC entry
opportunity in the direction the overshoot implies about crowd sentiment:
an extreme POSITIVE overshoot (MARA rallying much harder than BTC) signals
excess speculative enthusiasm concentrated in the leveraged proxy --
treated here as a bullish CONFIRMATION tell for BTC itself (following
the crowd's revealed high-conviction bet, not fading it), since MARA's
overshoot requires genuine risk-seeking capital rotating into the
highest-beta available vehicle.

Tested on the intended domain (BTC/USDT, ETH/USDT) AND on equity (QQQ, SPY)
as an explicit falsification check.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_gate_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _to_naive_daily(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.to_datetime(index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def _load_overshoot_gate(
    index: pd.DatetimeIndex,
    zscore_window: int,
    entry_z: float,
) -> pd.Series:
    """Load MARA (equity, leveraged bitcoin-mining proxy) and BTC/USDT
    (crypto, daily-resampled) closes, compute the MARA/BTC ratio's rolling
    z-score, and gate = True (risk-on / long allowed) whenever that z-score
    is at/above +entry_z (MARA overshooting BTC to the upside -- treated as
    a bullish crowd-conviction confirmation). Cached across calls within a
    process."""
    cache_key = (zscore_window, entry_z)
    if cache_key in _gate_cache:
        gate = _gate_cache[cache_key]
    else:
        from loaders import load_equity, load_crypto

        start = index.min().to_pydatetime() if len(index) else datetime(2019, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2015))

        mara_raw = _prep(load_equity("MARA", pad_start, end))["close"]
        mara_close = mara_raw.copy()
        mara_close.index = _to_naive_daily(mara_close.index)
        mara_close = mara_close[~mara_close.index.duplicated(keep="last")]

        btc_hourly = load_crypto("BTC/USDT", pad_start, end, interval="1h")
        btc_daily = _prep(btc_hourly)["close"].resample("1D").last().dropna()
        btc_daily.index = _to_naive_daily(btc_daily.index)
        btc_daily = btc_daily[~btc_daily.index.duplicated(keep="last")]

        common = mara_close.index.union(btc_daily.index)
        mara_aligned = mara_close.reindex(common).ffill()
        btc_aligned = btc_daily.reindex(common).ffill()
        ratio = (mara_aligned / btc_aligned).dropna()

        log_ratio = ratio.apply(lambda x: pd.NA if x <= 0 else x).dropna()
        import numpy as np
        log_ratio = log_ratio.apply(lambda x: float(np.log(x)))
        roll_mean = log_ratio.rolling(zscore_window).mean()
        roll_std = log_ratio.rolling(zscore_window).std()
        zscore = (log_ratio - roll_mean) / roll_std

        gate = (zscore >= entry_z).astype(int)
        _gate_cache[cache_key] = gate

    idx_naive = _to_naive_daily(index)
    reindexed = gate.reindex(idx_naive, method="ffill").fillna(0).astype(int)
    reindexed.index = index
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 100,
    zscore_window: int = 60,
    entry_z: float = 0.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND the MARA/BTC ratio's
    rolling z-score is at/above entry_z (MARA overshooting BTC to the
    upside -- bullish crowd-conviction confirmation); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    overshoot_gate = _load_overshoot_gate(df.index, zscore_window, entry_z)

    position = (own_trend_up.astype(int) & overshoot_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
