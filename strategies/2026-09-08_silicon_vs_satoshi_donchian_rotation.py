"""Strategy: Silicon vs Satoshi -- Donchian breakout rotation, QQQ/BTC/cash.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Quantpedia's "Silicon vs. Satoshi: Tactical Asset Rotation Between
NASDAQ-100 and Bitcoin" (https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/,
own-research article, 2 July 2026): QQQ and Bitcoin are "economic
substitutes in the retail attention marketplace," both drawing from the
same speculative-capital pool, so a Donchian-breakout-based rotation
between them (with a cash fallback during consolidation) should capture
whichever asset is currently attracting the marginal retail dollar while
avoiding both during flat/choppy periods. Source's exact rule: for a
lookback window w, the upper channel bound Ut(w) = max(close over trailing
w days); a breakout signal triggers when today's close exceeds that bound
(computed on trailing data, i.e. yesterday's rolling max, to avoid
look-ahead). Two priority variants: A (QQQ checked first, then BTC, then
cash) and B (BTC first, then QQQ, then cash). Source reports (2019-2025,
no transaction costs modeled) Sharpe ratios up to 1.69 (Variant A, 5-day
lookback) and 1.68 (Variant A, 20-day lookback), Calmar ratios above 2.2,
and max drawdowns 50-79% shallower than buy-and-hold, robust across the
5-30 day lookback range.

This is the first cross-asset QQQ/BTC Donchian-breakout rotation strategy
in this repo -- distinct from the already-tested dual-momentum GEM-style
rotation (2026-09-04-097, uses trailing 12-month RELATIVE momentum + 0%
absolute-momentum gate on a monthly rebalance, not a Donchian breakout on
a daily rebalance) and from single-asset Donchian breakout strategies
(e.g. 2026-09-08_vhf_regime_gated_donchian_breakout.py) which don't
rotate between two assets.

Because this repo's grid-test/validator contract expects a single
`generate_returns` series aligned to the PRIMARY asset's index, we
implement Variant A (QQQ first priority) with the primary asset = QQQ and
BTC fetched internally as the partner via data/loaders.py.load_crypto
(mirroring the pattern in strategies/2026-09-04_dual_momentum_rotation.py
and strategies/2026-09-08_rebalancing_premium_spread.py). Position is
rebalanced daily (source's own methodology), not monthly.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1}, 1 whenever
        ANY of QQQ/BTC is held, 0 when in cash)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns blending QQQ/BTC/cash depending on the daily breakout
        rotation)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner_close(partner_symbol: str, start, end) -> pd.Series:
    df = load_crypto(partner_symbol, start, end, interval="1d")
    df = _prep(df)
    return df["close"]


def _simulate(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_days: int = 20,
) -> pd.DataFrame:
    df = _prep(price_df)
    qqq_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    btc_close = _load_partner_close(partner_symbol, start, end)
    btc_close = btc_close.reindex(qqq_close.index, method="ffill")

    # Donchian upper bound computed on TRAILING data only (shift by 1 to
    # avoid look-ahead: today's breakout check uses yesterday's channel).
    qqq_upper = qqq_close.rolling(lookback_days).max().shift(1)
    btc_upper = btc_close.rolling(lookback_days).max().shift(1)

    qqq_breakout = qqq_close > qqq_upper
    btc_breakout = btc_close > btc_upper

    qqq_daily_ret = qqq_close.pct_change().fillna(0.0)
    btc_daily_ret = btc_close.pct_change().fillna(0.0)

    # Variant A: QQQ first priority, then BTC, then cash.
    holding = pd.Series("cash", index=qqq_close.index, dtype=object)
    holding[qqq_breakout.fillna(False)] = "qqq"
    still_cash = holding == "cash"
    holding[still_cash & btc_breakout.fillna(False)] = "btc"

    # Apply the decision made at today's close starting the NEXT trading
    # day (avoid using today's own close-derived signal on today's return).
    holding_applied = holding.shift(1).fillna("cash")

    strat_ret = pd.Series(0.0, index=qqq_close.index)
    strat_ret[holding_applied == "qqq"] = qqq_daily_ret[holding_applied == "qqq"]
    strat_ret[holding_applied == "btc"] = btc_daily_ret[holding_applied == "btc"]

    position = (holding_applied != "cash").astype(int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=qqq_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, partner_symbol, lookback_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    partner_symbol: str = "BTC/USDT",
    lookback_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, partner_symbol, lookback_days)
    return result["returns"]
