"""Strategy: Overnight-return premium, gated by trend AND a CALM-VIX regime.

Hypothesis (see knowledge_base/strategies_log.jsonl, this id), sourced from
Quantpedia "Market Sentiment and an Overnight Anomaly"
(https://quantpedia.com/strategies/market-sentiment-and-an-overnight-anomaly/,
paper: Vojtko/Hanicova, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3829582):
the source's own rule holds SPY overnight only when (a) price is above its
20-day moving average, (b) VIX is BELOW its own moving average (i.e. a CALM,
not elevated, volatility regime), and (c) a proprietary sentiment indicator
(Brain Market Sentiment, not available to us) is above its moving average.
Source reports Sharpe 2.12 / MDD -10.97% for this 3-signal overlay
(2018-2021 backtest).

This is the OPPOSITE polarity from this repo's already-rejected
2026-09-07-020 (overnight hold gated by ELEVATED VIX vs its rolling
median), whose own notes explicitly flagged this as the natural next test:
"a future loop could try the OPPOSITE gate (low-VIX / calm-regime only
hold) instead, since [the elevated-VIX gate] shows the high-vol-regime
overnight moves are what's dragging Sharpe/MDD down." This strategy
directly implements that suggested opposite-polarity refinement of the
already-accepted unconditional overnight-hold-trend-gate (2026-09-08-053),
adding the source's own VIX-calm-regime condition as a second gate on top
of the existing trend filter (dropping only the proprietary sentiment leg,
which we cannot replicate).

Signal logic
------------
- Overnight return for day t = open[t] / close[t-1] - 1 (position entered
  at the PRIOR day's close, exited at the current day's open; flat during
  the intraday session -- identical overnight-only construction as -053).
- Trend filter: close[t-1] > SMA(trend_window) as of t-1.
- VIX calm-regime filter: VIX close[t-1] < SMA(vix_window) of VIX close, as
  of t-1 (i.e. VIX currently BELOW its own recent average -- calm/low-fear
  regime, matching the source's own moving-average-based VIX condition,
  not a relative/percentile threshold).
- Position[t] = 1 iff BOTH filters are satisfied as of close[t-1]; else 0.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (overnight-only daily
        strategy returns, gated as above)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_vix_calm_flag(idx: pd.DatetimeIndex, vix_window: int) -> pd.Series:
    """Fetch ^VIX daily closes and return a boolean series: True when VIX
    close < its own rolling SMA(vix_window) (calm regime), reindexed/ffilled
    onto the strategy's own trading-day index. Falls back to "always calm"
    (True) if VIX data is unavailable (e.g. for a crypto primary being
    tested as a falsification check, or a data outage)."""
    from loaders import load_equity

    pad_days = vix_window * 3 + 30
    start = (idx.min() - pd.Timedelta(days=pad_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    try:
        vix_df = load_equity("^VIX", start=start, end=end)
        vix_close = vix_df.set_index("timestamp")["close"].sort_index()
        vix_close.index = (
            vix_close.index.tz_localize(None) if vix_close.index.tz is not None else vix_close.index
        )
    except Exception:
        return pd.Series(True, index=idx, dtype=bool)

    vix_sma = vix_close.rolling(vix_window).mean()
    calm = vix_close < vix_sma

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    calm = calm.reindex(calm.index.union(target_idx)).sort_index().ffill()
    calm = calm.reindex(target_idx)
    calm.index = idx
    return calm.fillna(True)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    vix_window: int = 20,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding overnight into this bar's open.

    Requires BOTH: close[t-1] > SMA(trend_window), AND VIX close[t-1] <
    SMA(vix_window) of VIX (calm regime).
    """
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    try:
        vix_calm = _get_vix_calm_flag(idx, vix_window)
    except Exception:
        vix_calm = pd.Series(True, index=idx, dtype=bool)

    combined = (trend_up.fillna(False) & vix_calm.fillna(True))
    # Decision to hold overnight INTO bar t is made using info known as of
    # the PRIOR close (t-1): shift the combined filter forward by 1 bar.
    position = combined.shift(1).fillna(False).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: open[t]/close[t-1] - 1, gated by
    trend + VIX-calm-regime filters."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    position = generate_signals(price_df, **kwargs)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
