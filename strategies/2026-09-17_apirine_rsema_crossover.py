"""Strategy: Apirine Relative Strength EMA (RS EMA) fast/slow crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) May 2022 Traders'
Tips (republishing the January 2022 article), Vitali Apirine, "Relative
Strength Moving Averages, Part 1: The Relative Strength Exponential Moving
Average (RS EMA)", via
https://traders.com/Documentation/FEEDbk_docs/2022/05/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage code:

    Mltp1 = 2 / (Periods + 1)
    Cup   = Close - Close[1] if Close > Close[1] else 0
    Cdwn  = Close[1] - Close if Close < Close[1] else 0
    RS    = |EMA(Cup, Pds) - EMA(Cdwn, Pds)| / (EMA(Cup, Pds) + EMA(Cdwn, Pds) + 1e-5)
    RS    = RS * Mltp   (Mltp default 10)
    Rate  = Mltp1 * (1 + RS)
    RS_EMA[t] = RS_EMA[t-1] + Rate * (Close - RS_EMA[t-1])

RS EMA is a PRICE-based (self-referential) adaptive-rate EMA: its own
up/down-day EMA asymmetry (RS, akin to a Wilder-style RSI numerator built
from EMA-smoothed Cup/Cdwn rather than raw close) speeds up the EMA during
strongly trending/asymmetric price action and slows it during choppy/
balanced action. This is DISTINCT from the already-rejected "Relative VIX
Strength EMA" (RSEMA, id=2026-09-12-184, TASC Mar 2022 companion article)
which drives its adaptive rate from a SECOND SYMBOL's (VIX) up/down-day
asymmetry rather than the traded asset's own price action -- and distinct
from the also-tested RS VolatAdj EMA (Mar 2022, same VIX-driven family,
skipped this iteration as non-novel). First pure-price-based RS EMA
strategy in this repo.

Trading rule (source article's own suggested use, per the March 2022
companion piece and this repo's standard treatment for a bare adaptive-MA
indicator): a fast RS EMA (short periods) crossing above a slow RS EMA
(long periods) is a bullish trend-turn signal (the source explicitly notes
"RS EMAs with different lengths can define turning points"); exit on the
reverse cross or a max_hold_days time-stop. A close>SMA(trend_window)
regime filter is added (this repo's standard robustness pattern for
crossover-only entries) to avoid buying fast/slow RS-EMA crosses inside an
established downtrend.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rs_ema(close: pd.Series, periods: int, pds: int, mltp: float) -> pd.Series:
    """Apirine's Relative Strength EMA, price-based adaptive-rate EMA."""
    mltp1 = 2.0 / (periods + 1)
    delta = close.diff()
    cup = delta.clip(lower=0.0).fillna(0.0)
    cdwn = (-delta).clip(lower=0.0).fillna(0.0)

    ema_up = cup.ewm(span=pds, adjust=False).mean()
    ema_dwn = cdwn.ewm(span=pds, adjust=False).mean()

    rs = (ema_up - ema_dwn).abs() / (ema_up + ema_dwn + 1e-5)
    rs = rs * mltp
    rate = (mltp1 * (1.0 + rs)).clip(upper=1.0)

    rs_ema = pd.Series(index=close.index, dtype=float)
    prev = None
    for i, (r, c) in enumerate(zip(rate.to_numpy(), close.to_numpy())):
        if prev is None or pd.isna(prev):
            prev = c
        else:
            prev = prev + r * (c - prev)
        rs_ema.iloc[i] = prev
    return rs_ema


def generate_signals(
    price_df: pd.DataFrame,
    fast_periods: int = 8,
    slow_periods: int = 25,
    rs_pds: int = 20,
    rs_mltp: float = 10.0,
    trend_window: int = 50,
    min_hold_days: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``min_hold_days`` adds a hysteresis gate (only allow an exit once the
    opposite raw signal has persisted for at least this many bars) to
    reduce whipsaw from fast/slow RS-EMA crossovers flipping quickly during
    choppy conditions -- the same fix pattern already validated on several
    other crossover strategies in this repo (e.g. Ehlers MAD zero-line
    crossover, strategies/2026-09-17_ehlers_mad_zeroline_crossover.py).
    """
    df = _prep(price_df)
    close = df["close"]

    fast_rs_ema = _rs_ema(close, fast_periods, rs_pds, rs_mltp)
    slow_rs_ema = _rs_ema(close, slow_periods, rs_pds, rs_mltp)
    trend_sma = close.rolling(trend_window).mean()

    bullish = (fast_rs_ema > slow_rs_ema) & (close > trend_sma)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = (not bool(bullish.iloc[i])) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish.iloc[i]):
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
