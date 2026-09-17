"""Strategy: Katsanos VIX-ETF Long System (TASC "Trading The Fear Index").

Source: TASC (Technical Analysis of Stocks & Commodities) August 2022,
Markos Katsanos, "Trading The Fear Index", via TradeStation EasyLanguage
disclosed at
https://traders.com/Documentation/FEEDbk_docs/2022/08/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl).

The source's disclosed "Long VIX ETF" system (intended for VXX/VIXY/UVXY/
VIXM/VXZ/SVOL) trades a LONG-VOLATILITY ETF using three ingredients, all
computed off the VIX index and SPY (not the traded ETF's own price):

    STVIXS/STVIXL = 3-bar-smoothed short/long-length %K stochastic of VIX
    STSPYS/STSPYL = same stochastic construction applied to SPY
    VIXUP = (today's VIX high / lowest VIX low over VBARS bars, prior bar) - 1, x100
    RC    = Pearson correlation of VIX level against a simple bar-index
            trend over (VBARS-1) bars ("correlation trend")

    BUYCONDITION = STVIXL > STSPYL AND STVIXS > STSPYS AND rising STVIXS
                   AND VIXUP > VIXUPMAX AND RC > 0.8 AND rising RC
    SELLCONDITION = STSPYS > STVIXS OR falling STVIXS

This repo is long-only (see SAFETY.md), so only the source's Long-VIX-ETF
BUYCONDITION/SELLCONDITION pair is used here (the mirror SHORTCONDITION/
COVERCONDITION legs, which bet on VIX ETF DECAY via a short position, are
dropped). This is the first strategy in this repo that trades a VIX-linked
ETF directly (e.g. VXX) using VIX/SPY as EXTERNAL FILTER DATA rather than
using VIX purely as a regime gate on an equity-index position (distinct
from Relative VIX Strength EMA id=2026-09-12-184, Katsanos capitulation
dual-stochastic id=2026-09-17-162, Apirine RS VolatAdj EMA family -- all of
which trade SPY/QQQ gated by VIX, not a VIX-linked instrument itself).

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

``price_df`` is the traded symbol's own OHLCV (e.g. VXX) -- VIX and SPY
auxiliary series are fetched internally via data/loaders.load_equity and
aligned to price_df's date index (VIX ticker '^VIX'; SPY tracked via a
`spy_symbol` param defaulting to "SPY" so a caller could substitute another
broad equity proxy if desired, though SPY is the source's own reference).
"""

from __future__ import annotations

import pandas as pd

from data.loaders import load_equity


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    lo = low.rolling(window).min()
    hi = high.rolling(window).max()
    raw = (close - lo) / (hi - lo + 0.0001) * 100.0
    return raw.rolling(3).mean()


def _correlation_trend(vix_close: pd.Series, window: int) -> pd.Series:
    bar_idx = pd.Series(range(len(vix_close)), index=vix_close.index, dtype=float)
    return vix_close.rolling(window).corr(bar_idx)


def _fetch_aux(price_df_index: pd.DatetimeIndex, spy_symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    start = price_df_index.min() - pd.Timedelta(days=400)
    end = price_df_index.max() + pd.Timedelta(days=5)
    vix_df = load_equity("^VIX", start.to_pydatetime(), end.to_pydatetime())
    spy_df = load_equity(spy_symbol, start.to_pydatetime(), end.to_pydatetime())
    if "timestamp" in vix_df.columns:
        vix_df = vix_df.set_index("timestamp")
    if "timestamp" in spy_df.columns:
        spy_df = spy_df.set_index("timestamp")
    return vix_df.sort_index(), spy_df.sort_index()


def generate_signals(
    price_df: pd.DataFrame,
    vixupmax: float = 50.0,
    vbars: int = 6,
    stbarsl: int = 25,
    stbarss: int = 10,
    spy_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} long/flat position series for a long-VIX-ETF ticker."""
    df = _prep(price_df)
    vix_df, spy_df = _fetch_aux(df.index, spy_symbol)

    vix = vix_df["close"].reindex(df.index, method="ffill")
    vix_h = vix_df["high"].reindex(df.index, method="ffill")
    vix_l = vix_df["low"].reindex(df.index, method="ffill")
    spy = spy_df["close"].reindex(df.index, method="ffill")
    spy_h = spy_df["high"].reindex(df.index, method="ffill")
    spy_l = spy_df["low"].reindex(df.index, method="ffill")

    st_vix_s = _stochastic(vix_h, vix_l, vix, stbarss)
    st_spy_s = _stochastic(spy_h, spy_l, spy, stbarss)
    st_vix_l = _stochastic(vix_h, vix_l, vix, stbarsl)
    st_spy_l = _stochastic(spy_h, spy_l, spy, stbarsl)

    vix_up = (vix_h / vix_l.rolling(vbars).min().shift(1) - 1.0) * 100.0
    rc_window = vbars - 1
    rc = _correlation_trend(vix, rc_window)

    buy_condition = (
        (st_vix_l > st_spy_l)
        & (st_vix_s > st_spy_s)
        & (st_vix_s > st_vix_s.shift(1))
        & (vix_up > vixupmax)
        & (rc > 0.8)
        & (rc > rc.shift(1))
    )
    sell_condition = (st_spy_s > st_vix_s) | (st_vix_s < st_vix_s.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(sell_condition.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(buy_condition.iloc[i]):
                in_position = True
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
