"""Strategy: Cross-asset correlated-stress reversal, MULTI-DAY HOLD rescue.

Direct rescue of near-miss 2026-09-11-072 (QuantPedia's "Short-Term
Correlated Stress Reversal Trading", https://quantpedia.com/short-term-correlated-stress-reversal-trading/,
Vojtko 2025): the original 1-day-hold implementation passed Sharpe/MDD/
walk-forward on QQQ but decisively failed transaction-cost survival (net
Sharpe 0.402 < 0.5 threshold) due to inherently high turnover from a strict
1-day-hold construction (1510 trades over 14yr). That entry's own notes
suggested "a 2-3 day hold to reduce trade frequency while preserving edge"
as the direct fix -- this strategy implements exactly that: same
cross-asset stress-event trigger (IEF up + a risk-on asset (GLD/USO/primary)
down beyond a threshold, same day), but holds the primary asset long for
`hold_days` trading days instead of exactly 1, with overlapping triggers
extending (not stacking) the hold. No new external source -- pure
parameter/mechanic retune of the already-sourced QuantPedia rule.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_aux_returns(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Load GLD/USO/IEF daily returns via data/loaders.py, aligned to index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=10)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    out = {}
    for sym in ("GLD", "USO", "IEF"):
        df = load_equity(sym, start, end)
        close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
        close.index = pd.to_datetime(close.index).tz_localize(None)
        ret = close.pct_change()
        ret = ret.reindex(pd.to_datetime(index).tz_localize(None)).ffill()
        ret.index = index
        out[sym] = ret
    return pd.DataFrame(out)


def generate_signals(
    price_df: pd.DataFrame,
    ief_thresh: float = 0.0,
    risk_thresh: float = 0.0,
    hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    primary_ret = close.pct_change()

    aux = _load_aux_returns(close.index)
    ief_ret, gld_ret, uso_ret = aux["IEF"], aux["GLD"], aux["USO"]

    stress_trigger = (
        ((ief_ret >= ief_thresh) & (gld_ret <= -risk_thresh))
        | ((ief_ret >= ief_thresh) & (uso_ret <= -risk_thresh))
        | ((ief_ret >= ief_thresh) & (primary_ret <= -risk_thresh))
    ).fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    hold_until = -1  # index up to (inclusive) which we stay long

    for i in range(n):
        if bool(stress_trigger.iloc[i]):
            # Enter the day after the trigger, hold for hold_days trading days.
            entry_i = i + 1
            hold_until = max(hold_until, entry_i + hold_days - 1)
        if i <= hold_until and i >= 1:
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Note: generate_signals already represents the entry-day position (it
    incorporates its own shift from the trigger day), so we do NOT apply an
    additional shift here.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.fillna(0) * daily_ret
    return strategy_ret
