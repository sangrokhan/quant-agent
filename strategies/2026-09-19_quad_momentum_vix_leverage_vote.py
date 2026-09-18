"""Strategy: 4-Factor Leverage Vote (VIX + SPX trend + VWO momentum + BND
momentum) monthly rotation, single-symbol adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-005):
Per Cesar Alvarez's "UPRO/TQQQ Leveraged ETF Strategy"
(https://alvarezquanttrading.com/blog/upro-tqqq-leveraged-etf-strategy/,
a reader-submitted rule tested and reported by Alvarez, read via
browser_exec after web_search DDGS backend returned unusable results this
iteration): a monthly-rebalanced rule votes on 4 independent risk-on
signals -- (A) VIX <= 25, (B) S&P 500 > its 200-day SMA, (C) VWO (emerging
markets) has positive blended 1-3-6-12-week momentum, (D) BND (aggregate
bond fund) has positive blended 1-3-6-12-week momentum -- where the
1-3-6-12W momentum score is avg(1mo_return*12, 3mo_return*4,
6mo_return*2, 12mo_return*1). If ALL 4 vote true: 2x leveraged long
(UPRO+TQQQ in the source; single-symbol adaptation applies
leverage_multiplier to the primary asset's own return). If 1-2 of the 4
are false: 1x unleveraged long (source's QQQ+SPY leg; here just the
primary asset's own return). If 3-4 of the 4 are false: hold TLT (source's
bond-market defensive leg; substituted here as TLT's own return, gated by
TLT's own SMA(200) per the source's stated 2022 lesson that TLT alone is
not a universal hedge -- same substitution pattern already used in
2026-09-18-104's SPY/SSO/TLT strategy).

This is a genuinely distinct construction from the already-tested
2026-09-18-104 (SPY/SSO/TLT, only 2 factors: VIX level + SPX trend) via
TWO additional independent cross-asset momentum votes (VWO emerging-market
momentum, BND aggregate-bond momentum) that must also confirm before full
leverage is applied -- a stricter, 4-factor risk-on gate rather than a
2-factor one.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position
        indicator; 1 whenever exposure != 0)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        return with the variable exposure levels described above)
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


def _momentum_1_3_6_12w(close: pd.Series) -> pd.Series:
    """avg(1W_ret*12, 3W_ret*4, 6W_ret*2, 12W_ret*1) -- weekly-bar-equivalent
    approximation using ~5 trading days per week on daily bars."""
    r1 = close.pct_change(5) * 12
    r3 = close.pct_change(15) * 4
    r6 = close.pct_change(30) * 2
    r12 = close.pct_change(60) * 1
    return (r1 + r3 + r6 + r12) / 4.0


def _regime_frame(
    price_df: pd.DataFrame,
    trend_window: int,
    vix_threshold: float,
    vix_symbol: str,
    vwo_symbol: str,
    bnd_symbol: str,
    tlt_symbol: str,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    vix_close = _load_aux_close(idx, vix_symbol)
    vwo_close = _load_aux_close(idx, vwo_symbol)
    bnd_close = _load_aux_close(idx, bnd_symbol)
    tlt_close = _load_aux_close(idx, tlt_symbol)

    spx_sma = close.rolling(trend_window).mean()
    tlt_sma = tlt_close.rolling(trend_window).mean()

    vote_a = (vix_close <= vix_threshold).fillna(False)
    vote_b = (close > spx_sma).fillna(False)
    vote_c = (_momentum_1_3_6_12w(vwo_close) > 0).fillna(False)
    vote_d = (_momentum_1_3_6_12w(bnd_close) > 0).fillna(False)

    vote_count = vote_a.astype(int) + vote_b.astype(int) + vote_c.astype(int) + vote_d.astype(int)
    tlt_bull = (tlt_close > tlt_sma).fillna(False)

    return pd.DataFrame(
        {
            "primary_ret": close.pct_change().fillna(0.0),
            "tlt_ret": tlt_close.pct_change().fillna(0.0),
            "vote_count": vote_count,
            "tlt_bull": tlt_bull,
        },
        index=idx,
    )


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vix_threshold: float = 25.0,
    leverage_multiplier: float = 2.0,
    rebalance_days: int = 21,
    vix_symbol: str = "^VIX",
    vwo_symbol: str = "VWO",
    bnd_symbol: str = "BND",
    tlt_symbol: str = "TLT",
) -> pd.Series:
    """Return a {0,1} position indicator (1 = any nonzero exposure leg)."""
    frame = _regime_frame(price_df, trend_window, vix_threshold, vix_symbol, vwo_symbol, bnd_symbol, tlt_symbol)
    n = len(frame)
    rebalance_mask = pd.Series(False, index=frame.index)
    if n:
        rebalance_mask.iloc[0] = True
        rebalance_mask.iloc[::rebalance_days] = True

    position = pd.Series(0, index=frame.index, dtype=int)
    state_votes = 0
    state_tlt_bull = False
    for i in range(n):
        if rebalance_mask.iloc[i]:
            state_votes = int(frame["vote_count"].iloc[i])
            state_tlt_bull = bool(frame["tlt_bull"].iloc[i])
        if state_votes >= 3:
            position.iloc[i] = 1  # leveraged or unleveraged long, either way "in" the market
        else:
            position.iloc[i] = 1 if state_tlt_bull else 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vix_threshold: float = 25.0,
    leverage_multiplier: float = 2.0,
    rebalance_days: int = 21,
    vix_symbol: str = "^VIX",
    vwo_symbol: str = "VWO",
    bnd_symbol: str = "BND",
    tlt_symbol: str = "TLT",
) -> pd.Series:
    """Return the daily strategy return series with variable exposure."""
    frame = _regime_frame(price_df, trend_window, vix_threshold, vix_symbol, vwo_symbol, bnd_symbol, tlt_symbol)
    n = len(frame)
    rebalance_mask = pd.Series(False, index=frame.index)
    if n:
        rebalance_mask.iloc[0] = True
        rebalance_mask.iloc[::rebalance_days] = True

    returns = pd.Series(0.0, index=frame.index)
    state_votes = 0
    state_tlt_bull = False
    for i in range(n):
        if rebalance_mask.iloc[i]:
            state_votes = int(frame["vote_count"].iloc[i])
            state_tlt_bull = bool(frame["tlt_bull"].iloc[i])
        if state_votes == 4:
            returns.iloc[i] = leverage_multiplier * frame["primary_ret"].iloc[i]
        elif state_votes >= 3:
            returns.iloc[i] = 1.0 * frame["primary_ret"].iloc[i]
        else:
            returns.iloc[i] = frame["tlt_ret"].iloc[i] if state_tlt_bull else 0.0
    return returns
