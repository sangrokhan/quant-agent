"""Strategy: BTC short-lag lead-lag momentum spillover into ETH.

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Multiple academic/industry sources on crypto lead-lag structure (e.g. the
"seesaw effect" and Bitcoin/altcoin causality literature surfaced this
iteration, plus a practitioner account in Business Insider -- Martin Cheung,
Pulsar Trading Capital -- describing "if bitcoin is up X% today and ether is
doing nothing, buy ether and expect a similar gain") argue BTC's price moves
propagate into large-cap altcoins like ETH with a SHORT lag (next-bar/
next-day), not the multi-week trailing-momentum horizon already tested in
this repo's 2026-09-08-143 network-momentum-spillover strategy (TLT neighbor,
neighbor_lookback in {10,20,40} days, rejected on MDD for equity and 0/36 for
crypto entirely -- that strategy never actually tested a short-horizon
BTC->ETH edge specifically, only a long-horizon TLT->equity edge and BTC as
"primary", not neighbor).

This strategy is a genuinely different mechanism from every prior ETH/BTC
attempt in this repo:
  - 2026-09-04-083 (ETH/BTC log-spread z-score mean reversion) -- assumes
    cointegration/mean-reversion of the RATIO; rejected (MDD 78.4%).
  - 2026-09-04-108 (ETH/BTC ratio MA-cross always-invested rotation) --
    always fully invested in one of two assets; rejected (MDD 79.2%).
  - 2026-09-08-084 (ETH/BTC ratio breakout + BTC-stability gate) -- trades
    the RATIO's own breakout structure; rejected.
  - 2026-09-08-143 (TLT->equity/BTC->crypto 20d momentum gate) -- long
    horizon (10-40 day) neighbor momentum, DIFFERENT neighbor family
    (bond ETF), never tested BTC->ETH short-lag specifically.
This one instead trades ETH's OWN price using BTC's very recent (1-3 day)
return as a pure directional confirmation signal -- no ratio, no ETH/BTC
spread, no multi-week lookback. It isolates whether a short-horizon
lead-lag/spillover edge exists at daily granularity, distinct from both
mean-reversion-of-the-ratio and long-horizon momentum-gate mechanisms
already exhausted.

Signal logic
------------
- Compute BTC/USDT's trailing `btc_lag_window`-day simple return (default 1
  day = literal "yesterday's BTC move").
- Long ETH/USDT (position=1) when that trailing BTC return exceeds
  `btc_return_threshold` (default 0.0, i.e. BTC was up at all); flat
  otherwise.
- Signal lagged by 1 day (decision uses BTC's already-closed bar, applied to
  ETH's NEXT bar) to avoid lookahead -- consistent with every other
  strategy in this repo.
- No use of ETH's own price history in the signal at all (pure spillover,
  same isolation principle as 2026-09-08-143).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

price_df is expected to be the ETH/USDT OHLCV frame (as returned by
data/loaders.py load_crypto); the BTC leg is fetched internally.
"""

from __future__ import annotations

import os
import sys

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btc_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch BTC/USDT close series aligned to the given index, via data/loaders.py."""
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
    btc_df = load_crypto("BTC/USDT", start=start, end=end, interval="1d")
    btc_df = _prep(btc_df)
    return btc_df["close"].reindex(index, method="ffill")


def _simulate(
    price_df: pd.DataFrame,
    btc_lag_window: int = 1,
    btc_return_threshold: float = 0.0,
) -> pd.DataFrame:
    df = _prep(price_df)
    eth_close = df["close"]
    start, end = df.index.min(), df.index.max()

    btc_close = _get_btc_series(eth_close.index, start, end)
    btc_trail_ret = btc_close.pct_change(btc_lag_window)

    raw_signal = (btc_trail_ret > btc_return_threshold).astype(int)
    # lag by 1 day: decision made on BTC's already-closed bar, applied to
    # the NEXT ETH bar (avoid lookahead).
    position = raw_signal.shift(1).fillna(0).astype(int)

    eth_daily_ret = eth_close.pct_change().fillna(0.0)
    strat_ret = position * eth_daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=eth_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    btc_lag_window: int = 1,
    btc_return_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, btc_lag_window, btc_return_threshold)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    btc_lag_window: int = 1,
    btc_return_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, btc_lag_window, btc_return_threshold)
    return result["returns"]
