"""Strategy: TQQQ/TECL Monthly Laggard Rotation + Defensive Sleeve + 8% Intramonth Stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-076, this
iteration): per https://finlab.finance/en/blog/us-mean-reversion-strategy
("Short-Term Mean Reversion Trading Strategy Backtest: The 3-Day Laggard Rule
Behind a 67% CAGR", read via browser_exec -- web_extract's DDGS backend is
search-only), the source's FULL disclosed rule is a MONTHLY-decision system
with three layers:

1. Regime filter: risk-on when QQQ close > SMA(200) AND QQQ's trailing
   126-day return > 0. Evaluated once per month (month-end).
2. Reversal rule: in risk-on, hold whichever of TQQQ/TECL had the LOWER
   trailing 3-day return AT the month-end decision point (buy the laggard,
   hold it for the whole following month).
3. Defensive sleeve: in risk-off, hold whichever of IEF/GLD/SHY has the
   best (3-month minus 1-month) momentum, instead of this repo's earlier
   simplification to flat.
4. Execution/risk control shared across the source's whole strategy family:
   ONE position at a time, monthly rebalance, and an 8% INTRAMONTH STOP on
   the leveraged leg (if the held leveraged fund draws down 8% intramonth
   from its entry price, exit to cash for the remainder of that month).

This is a DISTINCT, corrected implementation vs. the already-rejected
2026-09-27-075 in this repo (which mistakenly checked the laggard/regime
condition every trading day rather than monthly, and simplified risk-off to
flat with no defensive sleeve and no 8% stop) -- that rejection's own
decisive failure mode (MDD 40.8% vs 25% threshold) is exactly what the
source's own 8% intramonth stop + real defensive sleeve are designed to
prevent. This iteration tests whether faithfully implementing those two
missing risk-control pieces (which 075 explicitly flagged as an unimplemented
"future direction") rescues the strategy.

Adapted to this repo's single-asset generate_signals/generate_returns(
price_df, **params) contract: price_df is assumed to be the leveraged asset
(TQQQ by default); the other leg, QQQ regime inputs, and defensive-sleeve
candidates are all loaded internally via data/loaders.py (same pattern as
2026-09-27_tqqq_tecl_laggard_rotation_regime_gate.py and this repo's other
multi-symbol-internal-fetch precedents, e.g. 2026-09-08_pairs_zscore_cointegration.py).
NOTE: because this repo's generate_returns is scoped to ONE named symbol's
returns, when the defensive sleeve or the "other leg" would be selected for
a given month, this adaptation returns 0 (flat) for THIS symbol during that
month, understating the source's full-rotation combined-portfolio return --
an honest, conservative simplification, consistent with 2026-09-27-075's
precedent.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position, with
        the 8% intramonth stop expressed as an early exit within the return
        series computed by generate_returns; generate_signals reports the
        INTENDED monthly hold flag, before intramonth-stop adjustment, for
        simplicity/inspectability)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_close(index: pd.DatetimeIndex, symbol: str) -> pd.Series:
    key = ("close", symbol)
    if key in _cache:
        close = _cache[key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2013))
        close = _prep(load_equity(symbol, pad_start, end))["close"]
        _cache[key] = close
    return close.reindex(index, method="ffill")


def _month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on the last available trading day of each calendar month."""
    s = pd.Series(index=index, data=index.to_period("M"))
    is_last = s.ne(s.shift(-1))
    is_last.iloc[-1] = True
    return is_last


def _monthly_decision_series(
    index: pd.DatetimeIndex,
    own_close: pd.Series,
    other_symbol: str,
    regime_sma_window: int,
    regime_return_window: int,
    lag_window: int,
    defensive_symbols: tuple,
) -> pd.DataFrame:
    """Compute, at each month-end decision date, which asset to hold for the
    NEXT month: 'own' (this symbol is the laggard leveraged leg), 'other'
    (the other leveraged leg is the laggard), or one of defensive_symbols
    (risk-off), or 'cash'.
    """
    qqq_close = _load_close(index, "QQQ")
    other_close = _load_close(index, other_symbol)
    def_closes = {sym: _load_close(index, sym) for sym in defensive_symbols}

    above_sma = qqq_close > qqq_close.rolling(regime_sma_window).mean()
    pos_return = qqq_close.pct_change(regime_return_window) > 0
    risk_on = (above_sma & pos_return).fillna(False)

    own_lag = own_close.pct_change(lag_window)
    other_lag = other_close.pct_change(lag_window)
    own_is_laggard = (own_lag < other_lag).fillna(False)

    # 3mo - 1mo momentum for defensive sleeve (approx 63d / 21d trading days)
    def_scores = {}
    for sym, c in def_closes.items():
        mom = c.pct_change(63) - c.pct_change(21)
        def_scores[sym] = mom

    month_end = _month_end_mask(index)
    decisions = pd.Series(index=index, data="cash", dtype=object)

    me_idx = index[month_end]
    for dt in me_idx:
        if risk_on.loc[dt]:
            decisions.loc[dt] = "own" if own_is_laggard.loc[dt] else "other"
        else:
            scores_at_dt = {sym: def_scores[sym].loc[dt] for sym in defensive_symbols}
            scores_at_dt = {k: v for k, v in scores_at_dt.items() if pd.notna(v)}
            if scores_at_dt:
                decisions.loc[dt] = max(scores_at_dt, key=scores_at_dt.get)
            else:
                decisions.loc[dt] = "cash"

    # forward-fill month-end decisions across each following month (decision
    # made at month-end T applies to all days until month-end T+1)
    decisions_ffilled = decisions.where(month_end).ffill().shift(1)
    decisions_ffilled.iloc[0] = "cash"
    decisions_ffilled = decisions_ffilled.fillna("cash")

    _cache[("decisions_last",)] = decisions_ffilled
    return decisions_ffilled


def generate_signals(
    price_df: pd.DataFrame,
    other_symbol: str = "TECL",
    lag_window: int = 3,
    regime_sma_window: int = 200,
    regime_return_window: int = 126,
    stop_pct: float = 0.08,
    defensive_symbols: tuple = ("IEF", "GLD", "SHY"),
) -> pd.Series:
    """Return a {0,1} position series (1 = intended to hold THIS symbol this
    month per the monthly laggard-rotation decision, BEFORE the intramonth
    stop is applied -- see generate_returns for the stop-adjusted P&L).
    """
    df = _prep(price_df)
    decisions = _monthly_decision_series(
        df.index, df["close"], other_symbol, regime_sma_window,
        regime_return_window, lag_window, defensive_symbols,
    )
    return (decisions == "own").astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    other_symbol: str = "TECL",
    lag_window: int = 3,
    regime_sma_window: int = 200,
    regime_return_window: int = 126,
    stop_pct: float = 0.08,
    defensive_symbols: tuple = ("IEF", "GLD", "SHY"),
) -> pd.Series:
    """Position-weighted daily returns for THIS symbol, honoring the 8%
    intramonth stop: once held, if THIS symbol's cumulative return since the
    start of the current hold period drops below -stop_pct, exit to cash for
    the remainder of that month (re-evaluated at the next month-end).
    """
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    decisions = _monthly_decision_series(
        df.index, close, other_symbol, regime_sma_window,
        regime_return_window, lag_window, defensive_symbols,
    )
    intends_hold = (decisions == "own").astype(int)

    # Apply 8% intramonth stop: track cumulative return since entry into a
    # contiguous "intends_hold" block; if it dips below -stop_pct, force
    # position to 0 for the rest of that block.
    position = np.zeros(len(df), dtype=float)
    cum_since_entry = 1.0
    in_hold = False
    stopped_out = False
    intends_arr = intends_hold.to_numpy()
    ret_arr = daily_ret.to_numpy()

    for i in range(len(df)):
        if intends_arr[i] == 1:
            if not in_hold:
                # new hold block begins
                in_hold = True
                stopped_out = False
                cum_since_entry = 1.0
                position[i] = 1.0
            else:
                if stopped_out:
                    position[i] = 0.0
                else:
                    position[i] = 1.0
            if not stopped_out:
                cum_since_entry *= (1.0 + ret_arr[i])
                if cum_since_entry - 1.0 <= -stop_pct:
                    stopped_out = True
        else:
            in_hold = False
            stopped_out = False
            position[i] = 0.0

    position_series = pd.Series(position, index=df.index)
    # shift(1): decisions/stop state known at close of day i-1 determine
    # exposure held during day i's return
    strat_ret = daily_ret * position_series.shift(1).fillna(0.0)
    return strat_ret
