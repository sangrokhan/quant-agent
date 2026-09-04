"""Strategy: ETH/BTC relative-strength rotation (always-invested, switches
between ETH and BTC based on the ETH/BTC ratio's own trend direction).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-108):
Per multiple crypto-market sources (KuCoin's ETH/BTC ratio guide, PyQuantLab's
cross-sectional crypto momentum writeups) surfaced in this iteration's
search, the ETH/BTC price ratio itself trends persistently (multi-month
"alt season" vs "BTC dominance" cycles) and can be used as a relative-
strength rotation signal: hold ETH when the ratio is in an uptrend (above
its own moving average, i.e. ETH outperforming BTC), hold BTC when the
ratio is in a downtrend (BTC outperforming ETH). Unlike this repo's
already-tested ETH/BTC strategies -- 2026-09-04-083 (mean-REVERSION on the
z-scored ETH/BTC spread, rejected) and 2026-09-04-097 (dual-momentum
GEM-style with an absolute-momentum cash-safe-haven gate) -- this strategy
is a pure TREND-following relative-strength rotation with NO cash
position: it is always fully invested in whichever of ETH/BTC the ratio
currently favors, never flat.

Signal logic
------------
- ratio[t] = ETH_close[t] / BTC_close[t]
- ratio_sma[t] = SMA(ratio, ratio_window)
- If ratio[t] > ratio_sma[t]: hold ETH (position label = "ETH").
- Else: hold BTC (position label = "BTC").
- Daily strategy return = ETH_ret[t] if holding ETH else BTC_ret[t]
  (decision made using data available as of yesterday's close, applied to
  today's return, per this repo's standard shift convention).
- No skip-day/rebalance-frequency smoothing beyond the daily ratio check
  itself (a fast, always-in-market rotation, distinct from -097's monthly
  rebalance).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1}: 1 = holding
        ETH per the rotation signal, 0 = holding BTC -- NOT a flat/long
        distinction like every other strategy in this repo, since this
        strategy is always invested in one of the two assets)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns from whichever asset is currently held)

Note: `price_df` here is expected to be ETH/USDT's OHLCV (the "primary"
symbol passed by the grid harness); BTC/USDT is fetched internally via
data/loaders.py, mirroring the pattern used in
2026-09-04_spy_qqq_pairs_zscore.py and 2026-09-04_dual_momentum_rotation.py.
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


def _simulate(
    price_df: pd.DataFrame,
    hedge_symbol: str = "BTC/USDT",
    ratio_window: int = 30,
) -> pd.DataFrame:
    """`price_df` is treated as the ETH/USDT OHLCV; `hedge_symbol` (BTC/USDT
    by default) is the rotation partner, fetched internally."""
    df = _prep(price_df)
    eth_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)
    btc_df = _prep(load_crypto(hedge_symbol, start, end))
    btc_close = btc_df["close"].reindex(eth_close.index, method="ffill")

    ratio = eth_close / btc_close
    ratio_sma = ratio.rolling(ratio_window).mean()
    hold_eth = (ratio > ratio_sma).fillna(False)

    eth_ret = eth_close.pct_change().fillna(0.0)
    btc_ret = btc_close.pct_change().fillna(0.0)

    # Decision made using info as of yesterday's close, applied to today's return.
    hold_eth_shifted = hold_eth.shift(1).fillna(False)
    strat_ret = eth_ret.where(hold_eth_shifted, btc_ret)
    position = hold_eth.astype(int)

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    hedge_symbol: str = "BTC/USDT",
    ratio_window: int = 30,
) -> pd.Series:
    return _simulate(price_df, hedge_symbol=hedge_symbol, ratio_window=ratio_window)["position"]


def generate_returns(
    price_df: pd.DataFrame,
    hedge_symbol: str = "BTC/USDT",
    ratio_window: int = 30,
) -> pd.Series:
    return _simulate(price_df, hedge_symbol=hedge_symbol, ratio_window=ratio_window)["returns"]
