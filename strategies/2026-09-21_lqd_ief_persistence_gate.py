"""Strategy: LQD/IEF credit-spread ratio persistence gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Cesar Alvarez's "Market Timing with a Canary, Gold, Copper, LQD, IEF and
much more" (https://alvarezquanttrading.com/blog/market-timing-with-a-canary-
gold-copper-lqd-ief-and-much-more/, read via browser_exec this iteration --
Alvarez himself is relaying an offhand remark from Adam Robinson on The
Knowledge Project podcast that the ratio of LQD (investment-grade corporate
bond ETF) to IEF (7-10yr Treasury ETF) is a good market-timing indicator,
since corporate-bond spreads widening relative to Treasuries reflects
deteriorating credit conditions/risk appetite before equities react). Per
Alvarez's own operationalization of the vague podcast remark (precise
disclosed rule, since the podcast itself gave no numeric threshold):

    ratio = LQD close / IEF close
    Buy signal: ratio closes above its own 200-day EXPONENTIAL moving
        average for 5+ CONSECUTIVE days (persistence filter, reducing
        single-day-crossover whipsaw)
    Sell signal: ratio closes below its own 200-day EMA for 5+ consecutive
        days

Distinct from this repo's already-tested HYG/IEF GEM dual-momentum rotation
(2026-09-10-024, a relative/absolute-momentum ROTATION between two assets)
because this is a much simpler ABSOLUTE-LEVEL persistence gate (single
signal line vs its own EMA, with a consecutive-day confirmation requirement)
applied as a risk-on/risk-off GATE on the PRIMARY traded asset's own SMA
trend-following signal, not a rotation between LQD and IEF themselves.

Signal logic
------------
- Fetch LQD and IEF close series internally (data/loaders.py) over the
  primary asset's own date range.
- ratio = LQD_close / IEF_close; ratio_ema = EMA(ratio, ema_window=200).
- risk_on state machine: flips to True only after `persistence_days`
  CONSECUTIVE closes with ratio > ratio_ema; flips to False only after
  `persistence_days` consecutive closes with ratio < ratio_ema; otherwise
  holds the prior state (source's own "5+ days" persistence rule).
- Primary asset trend signal: close > SMA(trend_window) (this repo's
  standard construction).
- Long only when BOTH risk_on (credit-spread gate) AND the primary asset's
  own trend filter agree; flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive(ts):
    py = ts.to_pydatetime()
    return py.replace(tzinfo=None) if py.tzinfo is not None else py


def _load_aux_close(index: pd.DatetimeIndex, symbol: str) -> pd.Series:
    """Fetch an auxiliary symbol's close series, forward-filled onto index."""
    from loaders import load_equity  # data/loaders.py, via strategies/ sys.path convention

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    aux_df = load_equity(symbol, start, end)
    aux_df = _prep(aux_df)
    aux_close = aux_df["close"].reindex(index.union(aux_df.index)).sort_index().ffill()
    return aux_close.reindex(index)


def _risk_on_state(ratio: pd.Series, ratio_ema: pd.Series, persistence_days: int) -> pd.Series:
    above = ratio > ratio_ema
    below = ratio < ratio_ema
    n = len(ratio)
    state = pd.Series(False, index=ratio.index)
    cur_state = False
    above_streak = 0
    below_streak = 0
    for i in range(n):
        if bool(above.iloc[i]):
            above_streak += 1
            below_streak = 0
        elif bool(below.iloc[i]):
            below_streak += 1
            above_streak = 0
        else:
            above_streak = 0
            below_streak = 0

        if above_streak >= persistence_days:
            cur_state = True
        elif below_streak >= persistence_days:
            cur_state = False
        state.iloc[i] = cur_state
    return state


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    lqd_symbol: str = "LQD",
    ief_symbol: str = "IEF",
    ema_window: int = 200,
    persistence_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    lqd_close = _load_aux_close(idx, lqd_symbol)
    ief_close = _load_aux_close(idx, ief_symbol)
    ratio = lqd_close / ief_close
    ratio_ema = ratio.ewm(span=ema_window, min_periods=ema_window).mean()

    risk_on = _risk_on_state(ratio, ratio_ema, persistence_days)

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    position = (risk_on & trend_ok.fillna(False)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
