"""Strategy: Crypto Fear & Greed Index bullish price/sentiment divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-033):
Third construction on this cron trigger's verified-feasible api.alternative.me
Fear & Greed Index data source (2026-09-20-029 binary hysteresis, rejected;
2026-09-20-030 continuous sizing dial, accepted). This iteration applies a
genuinely distinct construction: classic bullish DIVERGENCE detection
(price makes a lower swing low over a rolling lookback window while the
Fear & Greed index simultaneously makes a HIGHER swing low at the same
bar) -- the standard technical-divergence framing already used elsewhere in
this repo for RSI/MACD/OBV/A-D-Line/Elder-Ray/BOP divergence variants,
applied here to a sentiment index instead of a price-derived oscillator.
Economic rationale: if price is making a fresh low but crowd sentiment is
NOT correspondingly making a fresh extreme-fear low, it suggests the
selling pressure is losing conviction relative to the prior low -- a
classic divergence "weakening momentum" signal. Entry confirmed by the
index subsequently ticking up off its own low (source-agnostic, standard
divergence-confirmation convention used throughout this repo's other
divergence strategies, e.g. 2026-09-05-048 Force Index divergence,
2026-09-06-135 Elder-Ray Bull Power divergence).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import json
import urllib.request

import numpy as np
import pandas as pd

_fng_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_fear_greed() -> pd.Series:
    if "fng" in _fng_cache:
        return _fng_cache["fng"]

    url = "https://api.alternative.me/fng/?limit=0&format=json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    records = payload["data"]
    idx = pd.to_datetime([int(r["timestamp"]) for r in records], unit="s", utc=True)
    values = pd.Series([float(r["value"]) for r in records], index=idx).sort_index()
    values.index = values.index.normalize()
    _fng_cache["fng"] = values
    return values


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 10,
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Bullish divergence: at bar t, close[t] is a `swing_window`-bar rolling
    low (fresh price low) while fng[t] is STRICTLY ABOVE its own value at
    the prior rolling-low bar `swing_window` bars back (sentiment did NOT
    make a correspondingly deep low). Entry confirmed within
    `confirm_window` bars once fng ticks up from its own local low. Exit on
    a fixed `max_hold_days` time-stop (standard convention for this repo's
    other divergence strategies without a separately disclosed exit rule).
    """
    df = _prep(price_df)
    close = df["close"]

    fng = _fetch_fear_greed().reindex(df.index, method="ffill")

    rolling_price_low = close.rolling(swing_window).min()
    is_price_swing_low = close <= rolling_price_low

    fng_at_prior_low_bar = fng.shift(swing_window)
    bullish_divergence = (is_price_swing_low & (fng > fng_at_prior_low_bar)).fillna(False)

    fng_rising = fng > fng.shift(1)
    confirm_ok = fng_rising.rolling(confirm_window, min_periods=1).apply(lambda x: x.any(), raw=True).astype(bool)

    entry = (bullish_divergence & confirm_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
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
