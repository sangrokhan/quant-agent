"""Strategy: VXX/VXZ VIX-futures-curve contango carry (short-front, long-mid).

Hypothesis (2026-09-27 KB entry, this iteration): the VIX futures term
structure spends most of its time in contango (mid-dated futures priced
above front-month, i.e. VXZ -- a mid-curve VIX ETN proxy -- tends to decay
more slowly than VXX, the front-month VIX ETN proxy) during calm markets, so
a short-VXX / long-VXZ pair captures the negative roll-yield spread while
the long VXZ leg partially hedges a volatility spike. Source:
https://wolfx.trade/whitepaper/vix-carry (WOLFX Research, 2026-04-24 --
"VIX Contango Carry (Hedged)" whitepaper, academic lineage cited: Eraker &
Wu 2017 JFE on VIX-ETN negative roll drift, Alexander & Korovilas 2013 JAI
on VXX/VXZ decay characterization, Carr & Wu 2009 RFS variance risk
premium). First VXX/VXZ contango-carry pair strategy in this repo (0 prior
KB hits for "VXZ"/"contango carry") -- distinct from the only prior
VIX-ETF-direct-trade entry (2026-09-17-166, Katsanos Long-VIX-ETF dual-
stochastic momentum system on VXX alone, rejected) since this is a
market-neutral PAIR carry trade on the term-structure spread itself, not a
directional VXX momentum system, and uses VXZ (mid-curve) as an explicit
second leg.

Per SAFETY.md (no real order-placement / short-selling execution code):
implemented as a pure numerical spread-return calculation exactly like this
repo's existing SPY/QQQ and ETH/BTC pairs strategies
(strategies/2026-09-04_spy_qqq_pairs_zscore.py) -- long VXZ / short VXX
notional combined into a single synthetic daily return series, no broker
calls.

Signal logic (adapted from the source's own disclosed rule, simplified to
this repo's single-return-series/no-options contract -- source's VIX-spot
gate is approximated here with a realized-vol-of-VXX proxy since this repo's
loaders don't expose a separate VIX index/VIX3M series):
    contango[t]  = (VXZ_close[t] - VXX_close[t]) / VXX_close[t]
    calm_regime  = VXX's own trailing realized vol <= its trailing median
                   (proxy for the source's "VIX spot < 30" gate)
    spy_uptrend  = SPY close > SPY SMA(spy_trend_window) (proxy for the
                   source's "SPY 6-month trailing return > 0" gate)
    entry: contango[t] > entry_contango AND calm_regime AND spy_uptrend
    exit:  contango[t] < exit_contango OR calm_regime flips False OR
           spy_uptrend flips False OR max_hold_days reached
    emergency exit: VXX's realized vol spikes past emergency_vol_mult x its
           trailing median (proxy for source's "VIX >= 40" emergency exit)

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)

Note: mirrors the existing pairs-strategy convention -- ``price_df`` here is
expected to be VXX's OHLCV (the "primary" symbol the grid harness passes
in); VXZ and SPY are fetched internally via data/loaders.py.
"""

from __future__ import annotations

import math
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _simulate(
    price_df: pd.DataFrame,
    hedge_symbol: str = "VXZ",
    spy_symbol: str = "SPY",
    entry_contango: float = 0.05,
    exit_contango: float = 0.02,
    vol_window: int = 20,
    vol_lookback: int = 252,
    spy_trend_window: int = 126,
    emergency_vol_mult: float = 1.8,
    max_hold_days: int = 60,
) -> pd.DataFrame:
    df = _prep(price_df)
    vxx_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    vxz_df = _prep(load_equity(hedge_symbol, start, end))
    vxz_close = vxz_df["close"].reindex(vxx_close.index, method="ffill")
    spy_df = _prep(load_equity(spy_symbol, start, end))
    spy_close = spy_df["close"].reindex(vxx_close.index, method="ffill")

    vxx_ret = vxx_close.pct_change().fillna(0.0)
    vxz_ret = vxz_close.pct_change().fillna(0.0)

    # Contango proxy: relative decay differential over a trailing window.
    # VXX (front-month) decays faster than VXZ (mid-curve) under contango --
    # NOT the raw price ratio (VXZ/VXX differ hugely in absolute unit price
    # for reasons unrelated to the futures curve, e.g. differing inception
    # NAV/reverse-splits, making a raw price-ratio a biased/non-stationary
    # proxy). Use each ETN's own trailing N-day cumulative return spread
    # instead: contango[t] = ret_N(VXZ)[t] - ret_N(VXX)[t] (positive when
    # VXX has been bleeding faster than VXZ, the contango-harvest regime).
    contango_window = 60
    vxx_roll_ret = vxx_close.pct_change(contango_window)
    vxz_roll_ret = vxz_close.pct_change(contango_window)
    contango = vxz_roll_ret - vxx_roll_ret

    vxx_log_ret = (vxx_close / vxx_close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = vxx_log_ret.rolling(vol_window).std()
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    calm_regime = (realized_vol <= vol_median).fillna(False)
    emergency = (realized_vol >= vol_median * emergency_vol_mult).fillna(False)

    spy_sma = spy_close.rolling(spy_trend_window).mean()
    spy_uptrend = (spy_close > spy_sma).fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    returns = pd.Series(0.0, index=df.index)

    in_trade = False
    entry_idx = 0

    for i in range(n):
        c = contango.iloc[i]
        if not in_trade:
            if (
                pd.notna(c)
                and c > entry_contango
                and bool(calm_regime.iloc[i])
                and bool(spy_uptrend.iloc[i])
            ):
                in_trade = True
                entry_idx = i
        else:
            held = i - entry_idx
            # Short VXX / long VXZ, 50/50 notional (equal-vega-at-entry, per
            # source's own "15% NAV, 50/50 split" sizing description; here
            # normalized to a unit-notional pair so validators see a
            # standard daily-return series).
            day_ret = 0.5 * (-vxx_ret.iloc[i]) + 0.5 * vxz_ret.iloc[i]
            returns.iloc[i] = day_ret
            position.iloc[i] = 1
            exit_now = (
                (pd.notna(c) and c < exit_contango)
                or (not bool(calm_regime.iloc[i]))
                or (not bool(spy_uptrend.iloc[i]))
                or bool(emergency.iloc[i])
                or held >= max_hold_days
            )
            if exit_now:
                in_trade = False

    return pd.DataFrame({"position": position, "returns": returns}, index=df.index)


def generate_signals(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    result = _simulate(price_df, **kwargs)
    return result["position"]


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    result = _simulate(price_df, **kwargs)
    return result["returns"]
