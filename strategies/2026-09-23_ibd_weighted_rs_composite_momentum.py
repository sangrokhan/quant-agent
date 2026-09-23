"""Strategy: IBD-style weighted Relative Strength (RS) momentum vs benchmark.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Investor's Business Daily's classic "RS Rating" formula weights recent
performance more heavily than older performance: 40% weight on the most
recent 3-month (63 trading day) return, and 20% weight each on the 6-month
(126d), 9-month (189d) and 12-month (252d) returns -- source: multiple
independent write-ups (TradingView "IBD" script library, Shibui Finance RS
Rating Screener, Stockbee "IBD 200" methodology) all describing the same
40/20/20/20 weighted-quarter composite, double-weighting the most recent
quarter. This differs from every prior RS-line entry in this repo (e.g.
2026-09-09-039 IBD RS-line-at-new-high breakout confirmation,
2026-09-10-095 RS-ratio-crossing-its-own-MA) which used a SIMPLE
price-ratio-vs-MA construction, not IBD's actual disclosed weighted-quarter
composite formula computed directly on the traded symbol's own multi-period
returns (not a ratio series).

We hypothesize: a stock/coin whose own weighted-quarter RS composite score
(computed the same way IBD computes it, but expressed as raw weighted return
rather than a percentile rank against the whole market, since this repo's
data loaders only fetch single symbols) is strongly positive indicates
persistent multi-horizon momentum consensus (not just a single-period spike)
and should be followed with a trend-following long entry; when the composite
turns negative, momentum has broken down across multiple horizons
simultaneously and we should be flat.

Signal logic
------------
- weighted_rs = 0.4 * return(3mo) + 0.2 * return(6mo) + 0.2 * return(9mo)
  + 0.2 * return(12mo), where return(Nmo) = close / close.shift(N_trading_days) - 1
  (63/126/189/252 trading days respectively, the standard IBD convention).
- Long when weighted_rs > entry_threshold (default 0.0, i.e. net-positive
  composite momentum across all 4 horizons combined).
- Exit (flat) when weighted_rs < exit_threshold (default 0.0, symmetric,
  i.e. no hysteresis band by default but exit_threshold is a separate
  tunable so a hysteresis/deadband variant can be grid-tested).
- Optional max_hold_days cap to avoid indefinitely-long holds through a
  slow momentum decay before the composite formally crosses zero.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
Both accept price_df (OHLCV DataFrame with columns timestamp/open/high/low/
close/volume, as returned by data/loaders.py) and the strategy's tunable
parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weighted_rs(close: pd.Series, w3: int = 63, w6: int = 126, w9: int = 189, w12: int = 252) -> pd.Series:
    r3 = close / close.shift(w3) - 1.0
    r6 = close / close.shift(w6) - 1.0
    r9 = close / close.shift(w9) - 1.0
    r12 = close / close.shift(w12) - 1.0
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12


def generate_signals(
    price_df: pd.DataFrame,
    w3: int = 63,
    w6: int = 126,
    w9: int = 189,
    w12: int = 252,
    entry_threshold: float = 0.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    weighted_rs = _weighted_rs(close, w3, w6, w9, w12)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_days = 0
    for i in range(len(close)):
        rs = weighted_rs.iloc[i]
        if pd.isna(rs):
            position.iloc[i] = 1 if in_pos else 0
            if in_pos:
                hold_days += 1
            continue
        if not in_pos:
            if rs > entry_threshold:
                in_pos = True
                hold_days = 0
        else:
            hold_days += 1
            if rs < exit_threshold or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        position.iloc[i] = 1 if in_pos else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    w3: int = 63,
    w6: int = 126,
    w9: int = 189,
    w12: int = 252,
    entry_threshold: float = 0.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        w3=w3,
        w6=w6,
        w9=w9,
        w12=w12,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change()
    # Position at t-1 determines exposure to the t return (avoid lookahead).
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret.fillna(0.0)
