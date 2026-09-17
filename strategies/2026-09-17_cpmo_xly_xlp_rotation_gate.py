"""Strategy: Apirine Compare Price Momentum Oscillator (CPMO) cross-asset gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-158):
Vitali Apirine's Traders' Tips article (TASC Aug 2020, "The Compare Price
Momentum Oscillator (CPMO)", source: Traders.com Aug 2020 Traders' Tips,
Wealth-Lab code read this iteration) applies the DecisionPoint Price
Momentum Oscillator (PMO -- a double-EMA-smoothed 1-period rate-of-change
oscillator, already saturated in this repo as a single-asset signal-vs-own-
line strategy) in an INTERMARKET context: compute PMO independently for two
different assets/sectors and trade the CROSSOVER of one PMO series above/
below the other, rather than an asset's PMO vs its own EMA signal line. The
source's reference example uses consumer discretionary (IXY) vs consumer
staples (IXR): PMO(discretionary) crossing above PMO(staples) is read as a
risk-on rotation signal for the broad market. This is a genuinely novel
mechanic in this repo (cross-asset PMO comparison, not single-asset PMO
signal-line crossover) even though the underlying PMO formula itself is
saturated. Adapted here: XLY (consumer discretionary) vs XLP (consumer
staples) sector ETF PMO comparison gates a long position in the traded
asset (SPY/QQQ/crypto).

Formula (per source)
---------------------
- ROC = 1-period rate of change (pct_change) of Price.
- EMAofROC(t) = EMAofROC(t-1)*(1-2/Period1) + ROC(t)*(2/Period1)
- PMOOsc(t) = PMOOsc(t-1)*(1-2/Period2) + EMAofROC(t)*10*(2/Period2)
- PMO(XLY) and PMO(XLP) computed independently with the same Period1/Period2.

Signal logic (long-only adaptation of the cross-asset comparison)
------------------------------------------------------------------------
- Entry (long, traded asset): PMO(XLY) crosses above PMO(XLP) (risk-on
  rotation signal).
- Exit: PMO(XLY) crosses below PMO(XLP) (risk-off rotation), OR after
  `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _pmo(price: pd.Series, period1: int, period2: int) -> pd.Series:
    roc = price.pct_change() * 100
    smoothing1 = 2.0 / period1
    smoothing2 = 2.0 / period2

    ema_of_roc = roc.ewm(alpha=smoothing1, adjust=False).mean()
    pmo = (ema_of_roc * 10).ewm(alpha=smoothing2, adjust=False).mean()
    return pmo


def _naive(ts):
    py = ts.to_pydatetime()
    return py.replace(tzinfo=None) if py.tzinfo is not None else py


def _load_sector_pmo(index: pd.DatetimeIndex, symbol: str, period1: int, period2: int) -> pd.Series:
    from loaders import load_equity  # data/loaders.py, already on sys.path via strategies/ caller convention

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    df = _prep(load_equity(symbol, start, end))
    pmo = _pmo(df["close"], period1, period2)
    pmo = pmo.reindex(index.union(pmo.index)).sort_index().ffill()
    return pmo.reindex(index)


def generate_signals(
    price_df: pd.DataFrame,
    period1: int = 35,
    period2: int = 20,
    max_hold_days: int = 30,
    risk_on_symbol: str = "XLY",
    risk_off_symbol: str = "XLP",
) -> pd.Series:
    """Return a {0,1} long/flat position series (long the traded asset)."""
    df = _prep(price_df)
    close = df["close"]

    pmo_on = _load_sector_pmo(df.index, risk_on_symbol, period1, period2)
    pmo_off = _load_sector_pmo(df.index, risk_off_symbol, period1, period2)

    bullish_cross = (pmo_on.shift(1) <= pmo_off.shift(1)) & (pmo_on > pmo_off)
    bearish_cross = (pmo_on.shift(1) >= pmo_off.shift(1)) & (pmo_on < pmo_off)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    warmup = period1 + period2
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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
