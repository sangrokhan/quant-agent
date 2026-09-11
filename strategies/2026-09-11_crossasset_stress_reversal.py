"""Strategy: Cross-asset correlated-stress reversal (long SPY/QQQ for 1 day
after a synchronized multi-asset stress event).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-072):
Per QuantPedia's "Short-Term Correlated Stress Reversal Trading"
(https://quantpedia.com/short-term-correlated-stress-reversal-trading/,
visited this iteration -- full methodology disclosed, Vojtko 2025), a
correlated stress event -- where a risk-off asset (US Treasuries, IEF)
RISES while a risk-on asset (equities SPY, oil USO, or gold GLD) FALLS
beyond a small dynamic threshold on the SAME day -- is a higher-conviction
signal of a systemic overreaction/flight-to-safety panic than a decline in
any single asset alone. The source's own optimal threshold across all
tested pairs is between 0% and -0.5% for the falling risky asset (or 0%
to +0.5% for the rising risk-off asset). The source's disclosed
methodology: on a stress day, buy the primary asset (SPY performed best
of the five candidates tested) at that day's close and liquidate at the
next day's close (a strict 1-day holding period, source's own diversified
composite strategy averages three IEF-vs-{GLD,USO,SPY} signal pairs).

This is the first strategy in this repo to use a CROSS-ASSET-CONFIRMED
stress-day signal (IEF up AND a risky asset down, same day) as a
mean-reversion entry trigger; distinct from prior single-asset drawdown/
Ulcer-Index/VIX-level triggers and from the already-tested HYG/LQD credit
z-score regime GATE (2026-09-05-025, a slow multi-day regime filter, not a
same-day stress-event 1-day-hold reversal trade).

Signal logic
------------
- Load GLD, USO, IEF via data/loaders.py (independent of whatever price_df
  is passed in as the primary tradable asset -- intended to be run with
  SPY or QQQ as price_df).
- Daily returns for the primary asset (SPY equivalent, whatever price_df
  is), GLD, USO, IEF.
- Stress-day trigger (source's diversified 3-signal composite, OR'd
  together): on day t,
    (a) IEF return >= +ief_thresh AND GLD return <= -risk_thresh, OR
    (b) IEF return >= +ief_thresh AND USO return <= -risk_thresh, OR
    (c) IEF return >= +ief_thresh AND primary-asset return <= -risk_thresh
- On a stress-triggered day, go long the primary asset for exactly ONE
  trading day (enter at that day's close, exit at next day's close, per
  source's disclosed methodology) -- implemented as position=1 on day t+1
  only (since generate_returns already shifts position by 1 day to apply
  yesterday's-close-to-today's-close return, an entry signal on day t
  should produce position=1 at day t+1, capturing the close(t)->close(t+1)
  return).
- Flat all other days (no compounding/overlap of stress signals; a fresh
  trigger while already in the 1-day hold simply keeps/extends the long
  by one more day, per the "one-day-at-a-time" liquidate-and-possibly-
  re-enter mechanic).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
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
) -> pd.Series:
    """Return a {0,1} long/flat position series (already shifted to entry day)."""
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

    # Enter the day AFTER the stress trigger (position at t+1 captures the
    # close(t)->close(t+1) 1-day-hold return the source's methodology uses).
    position = stress_trigger.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Note: generate_signals already represents the entry-day position (it
    incorporates its own 1-day shift from the trigger day), so here we do
    NOT apply an additional shift -- the position series IS today's
    exposure, unlike other strategies in this repo whose generate_signals
    returns a same-day trigger that generate_returns then shifts.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.fillna(0) * daily_ret
    return strategy_ret
