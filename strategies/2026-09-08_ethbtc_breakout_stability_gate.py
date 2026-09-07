"""Strategy: ETH/BTC ratio breakout rotation, gated by BTC price stability.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-084),
sourced from https://voiceofchain.com/academy/btc-dominance-trading-strategy
("BTC Dominance Trading Strategy: Entries, Exits and Risk"). Source's own
disclosed rotation rule (as a BTC-dominance/altcoin-rotation regime read,
proxied here via ETH/BTC since this repo has no total-market-cap/BTC.D
data source):

    "My preferred rotation signal is a BTC.D rejection from resistance
    while BTC holds above a key higher-low... ETH/BTC breaks a local high
    or holds a higher-low... I do not rotate just because dominance drops
    0.5%. I want confirmation from ETH/BTC, stable BTC price action."

Table: "Falling [dominance] / Sideways [BTC price] -> Best altcoin rotation
setup."

Operationalized (BTC.D unavailable, proxy with ETH/BTC ratio structure
only): long ETH/USDT when (1) the ETH/BTC ratio breaks above its own
N-day rolling high (the "ETH/BTC breaks a local high" trigger) AND (2) BTC
itself is in a stable/non-crashing regime (BTC's own N-day realized
volatility below its trailing median -- a proxy for the source's "BTC
price stays above its prior swing low" / "BTC stable" precondition, since
the source explicitly warns against rotating into alts when BTC itself is
falling hard). Exit when the ratio closes back below its own EMA basis or
a max_hold_days time-stop.

Distinct from the already-rejected plain ETH/BTC MA-cross always-invested
rotation (2026-09-04-108) by (a) using a BREAKOUT trigger (Donchian-style)
rather than a simple moving-average cross, (b) adding the BTC-stability
regime gate the source explicitly requires, and (c) being long-only/flat
(not always-invested rotating between ETH and BTC).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        price_df here is expected to be the ETH/USDT OHLCV frame; the BTC
        leg is fetched internally via data/loaders.py.
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btc_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch BTC/USDT close series aligned to the given index, via data/loaders.py."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_crypto  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)
    btc_df = load_crypto("BTC/USDT", start=start, end=end)
    btc_df = _prep(btc_df)
    return btc_df["close"].reindex(index).ffill()


def generate_signals(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    exit_ema_window: int = 10,
    btc_vol_window: int = 20,
    btc_vol_lookback: int = 90,
    btc_stability_ratio: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (ETH leg)."""
    df = _prep(price_df)
    close_eth = df["close"]
    close_btc = _get_btc_series(df.index)

    ratio = close_eth / close_btc
    rolling_high = ratio.rolling(breakout_window).max()
    breakout = ratio >= rolling_high.shift(1)
    ema_basis = ratio.ewm(span=exit_ema_window, adjust=False).mean()

    btc_log_ret = (close_btc / close_btc.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    btc_vol = btc_log_ret.rolling(btc_vol_window).std() * (252 ** 0.5)
    btc_vol_median = btc_vol.rolling(btc_vol_lookback, min_periods=btc_vol_window).median()
    btc_stable = btc_vol <= (btc_vol_median * btc_stability_ratio)

    entry = breakout & btc_stable.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            exit_signal = (
                not pd.isna(ema_basis.iloc[i]) and ratio.iloc[i] < ema_basis.iloc[i]
            )
            if exit_signal or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            trig = entry.iloc[i]
            if bool(trig) if pd.notna(trig) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns of the ETH leg (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
