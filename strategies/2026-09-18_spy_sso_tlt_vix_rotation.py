"""Strategy: SPY/SSO/TLT monthly rotation gated by SMA200 trend + VIX level.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per Cesar Alvarez / Alvarez Quant Trading's "SPY, SSO and TLT Strategy"
(https://alvarezquanttrading.com/blog/spy-sso-and-tlt-strategy/, fully
disclosed rules, read via browser_exec this iteration): a reader-submitted
monthly rotation strategy that leans into 2x-leveraged SSO during low-VIX
bull markets, holds SPY unleveraged during higher-VIX bull markets, and
switches to TLT during bear markets -- captured directly by trading a
SINGLE symbol (the primary equity asset, e.g. QQQ/SPY) with a variable
exposure multiplier rather than literally switching tickers (this repo's
generate_signals/generate_returns interface trades one `price_df` symbol at
a time; the source's SSO/TLT legs are approximated as continuous EXPOSURE
levels on the primary asset -- 2.0x when SSO-eligible, 1.0x when
SPY-eligible, and for the "bond" leg we fetch TLT's own daily return
in place of the primary's return since bond behavior cannot be approximated
by scaling the equity exposure to 0).

Source's own final (best MDD/CAR tradeoff) rule set, evaluated on the last
trading day of each month, applied here every day (daily reevaluation) using
a `rebalance_days` monthly cadence to mirror the source's monthly rebalance
without look-ahead:
  1. If primary close > primary SMA(200): bull regime.
       a. If VIX close < vix_threshold (default 25): SSO-equivalent, i.e.
          leverage_multiplier (default 2.0) x primary daily return.
       b. Else: SPY-equivalent, i.e. 1.0x primary daily return.
  2. Else (primary close <= primary SMA(200)): bear regime.
       a. If TLT close > TLT SMA(200): hold TLT (its own daily return).
       b. Else: cash (0 return) -- source's own 2022 lesson that TLT is not
          a universal bear-market hedge.

This differs from every prior SMA(200)-trend-gated strategy in this repo
(sizing-dial family, dual-momentum GTAA, etc.) in two ways: (a) it uses an
independent cross-asset VIX-level threshold to decide the LEVERAGE tier
within the bull regime (2x vs 1x), not just a binary on/off gate, and (b)
during the bear-regime leg it substitutes an entirely different asset's
(TLT's) own return series, gated by TLT's OWN trend filter -- rather than
just going flat or applying an inverse-vol overlay to the primary asset.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat,
        for the purpose of validators that need a position-indicator series;
        1 whenever exposure != 0, i.e. bull-any-tier or TLT-bear-hedge, 0
        only in the cash leg)
    generate_returns(price_df, **params) -> pd.Series  (the actual daily
        strategy return with the variable exposure levels described above)
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
    from loaders import load_equity  # data/loaders.py, on sys.path via strategies/ caller convention

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    aux_df = load_equity(symbol, start, end)
    aux_df = _prep(aux_df)
    aux_close = aux_df["close"].reindex(index.union(aux_df.index)).sort_index().ffill()
    return aux_close.reindex(index)


def _regime_frame(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vix_threshold: float = 25.0,
    vix_symbol: str = "^VIX",
    tlt_symbol: str = "TLT",
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()

    vix_close = _load_aux_close(df.index, vix_symbol)
    tlt_close = _load_aux_close(df.index, tlt_symbol)
    tlt_sma = tlt_close.rolling(trend_window).mean()
    tlt_ret = tlt_close.pct_change().reindex(df.index).fillna(0.0)
    primary_ret = close.pct_change().fillna(0.0)

    bull = close > sma
    tlt_bull = tlt_close > tlt_sma
    low_vix = vix_close < vix_threshold

    out = pd.DataFrame(index=df.index)
    out["bull"] = bull
    out["low_vix"] = low_vix
    out["tlt_bull"] = tlt_bull
    out["primary_ret"] = primary_ret
    out["tlt_ret"] = tlt_ret
    return out


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vix_threshold: float = 25.0,
    leverage_multiplier: float = 2.0,
    rebalance_days: int = 21,
    vix_symbol: str = "^VIX",
    tlt_symbol: str = "TLT",
) -> pd.Series:
    """Return a {0,1} position indicator (1 = any nonzero exposure leg)."""
    frame = _regime_frame(price_df, trend_window, vix_threshold, vix_symbol, tlt_symbol)
    n = len(frame)
    rebalance_mask = pd.Series(False, index=frame.index)
    if n:
        rebalance_mask.iloc[0] = True
        rebalance_mask.iloc[::rebalance_days] = True

    position = pd.Series(0, index=frame.index, dtype=int)
    state_bull = False
    state_low_vix = False
    state_tlt_bull = False
    for i, ts in enumerate(frame.index):
        if rebalance_mask.iloc[i]:
            state_bull = bool(frame["bull"].iloc[i])
            state_low_vix = bool(frame["low_vix"].iloc[i])
            state_tlt_bull = bool(frame["tlt_bull"].iloc[i])
        if state_bull:
            position.iloc[i] = 1
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
    tlt_symbol: str = "TLT",
) -> pd.Series:
    """Return the daily strategy return series with variable exposure."""
    frame = _regime_frame(price_df, trend_window, vix_threshold, vix_symbol, tlt_symbol)
    n = len(frame)
    rebalance_mask = pd.Series(False, index=frame.index)
    if n:
        rebalance_mask.iloc[0] = True
        rebalance_mask.iloc[::rebalance_days] = True

    returns = pd.Series(0.0, index=frame.index)
    state_bull = False
    state_low_vix = False
    state_tlt_bull = False
    for i in range(n):
        if rebalance_mask.iloc[i]:
            state_bull = bool(frame["bull"].iloc[i])
            state_low_vix = bool(frame["low_vix"].iloc[i])
            state_tlt_bull = bool(frame["tlt_bull"].iloc[i])
        if state_bull:
            mult = leverage_multiplier if state_low_vix else 1.0
            returns.iloc[i] = mult * frame["primary_ret"].iloc[i]
        else:
            returns.iloc[i] = frame["tlt_ret"].iloc[i] if state_tlt_bull else 0.0
    return returns
