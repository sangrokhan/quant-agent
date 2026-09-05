"""Strategy: XLU/SPY ratio 4-week rate-of-change "Beta Rotation" risk regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-067):
Per Michael Gayed's "Lead-Lag Report" (leadlagreport.com), the "Beta
Rotation" signal is described repeatedly across weekly issues as: the
4-week rate-of-change (ROC) of the XLU/SPY ratio flipping from negative to
positive marks a shift from Risk-On to Risk-Off (e.g. "The framework's
core risk check (XLU/SPY 4-week ROC) flipped from Risk-On to Risk-Off at
+8.34%"; "XLU/SPY 4-week RoC of +1.65% ... remains Risk-Off"; "-12.28%
... remains Risk-On"). Utilities (XLU, a low-beta defensive sector)
OUTPERFORMING the broad market (SPY) over the trailing 4 weeks (positive
ROC of the ratio) signals a defensive rotation (risk-off); utilities
underperforming (negative ROC) signals risk appetite / beta chasing
(risk-on). This is a NEW indicator pair (XLU/SPY) not yet tested in this
repo -- distinct from all prior cross-asset ratio regime filters (gold/
silver id=2026-09-05-030, copper/gold id=2026-09-05-032, XLY/XLP id=
2026-09-05-038, IWM/SPY id=2026-09-05-039, RSP/SPY id=2026-09-05-034,
SPY/TLT id=2026-09-05-036) both in the specific pair (defensive-sector vs
broad-market beta rotation) and in mechanism (rate-of-change sign flip
rather than SMA-crossover or z-score threshold).

Signal logic:
    ratio = XLU_close / SPY_close (using the strategy's OWN price_df is
    the SPY-analog symbol passed in by the grid; ratio computed against a
    fixed XLU series loaded internally)
    roc_4w = ratio.pct_change(periods=roc_window)  # ~4 trading weeks = 20d
    Long (risk-on) when roc_4w < 0 (XLU underperforming); flat (risk-off)
    when roc_4w >= 0 (XLU outperforming), holding prior state during NaN
    warmup.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly). Since this is a
regime-filter-on-a-different-asset strategy, XLU data is fetched
internally via data/loaders.py.load_equity (cache-first), keyed off the
SAME date range as price_df.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_xlu(start, end) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    xlu_df = load_equity("XLU", start, end)
    xlu_df = xlu_df.set_index("timestamp") if "timestamp" in xlu_df.columns else xlu_df
    return xlu_df.sort_index()["close"]


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long (risk-on) when the XLU/underlying ratio's roc_window-bar rate of
    change is negative (utilities underperforming); flat (risk-off) when
    positive (utilities outperforming, defensive rotation).
    """
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    xlu_close = _load_xlu(start, end)
    xlu_close = xlu_close.reindex(close.index).ffill()

    ratio = xlu_close / close
    roc = ratio.pct_change(periods=roc_window)

    risk_on = roc < 0
    position = risk_on.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
