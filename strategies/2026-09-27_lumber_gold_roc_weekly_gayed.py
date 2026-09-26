"""Strategy: Lumber/Gold "RORO" regime filter -- EXACT Gayed 13-week-ROC
comparison + weekly rebalance construction (distinct from repo's prior
2026-09-05-059 ratio-momentum construction).

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per https://allocatesmartly.com/the-lumber-gold-strategy/ (Michael Gayed's
"Risk On / Risk Off" indicator, found via Google AI-overview synthesis,
browser_exec since web_search DDGS backend is failing this session): at the
close on the last trading day of each week, compute the 13-week (roughly 65
trading-day) rate of return separately for lumber (WOOD ETF proxy, no
futures access via yfinance) and gold (GLD). If lumber's 13-week return
exceeds gold's, allocate to equities (risk-on); otherwise shift to a
defensive/flat posture (source uses cash/T-bills; here flat, no bond leg,
per this repo's single-price_df generate_returns contract, same
simplification already used and documented in 2026-09-05-059).

Distinct from this repo's already-rejected 2026-09-05-059 (Lumber/Gold
ratio's OWN momentum vs its lookback value, daily-rebalanced) in TWO ways
that materially change the mechanic: (1) compares the two SEPARATE ROC
series directly (source's actual disclosed rule) rather than one ratio
series' own momentum, and (2) rebalances WEEKLY (signal computed and
locked at each week's last trading day, held constant through the
following week) rather than continuously daily, matching the source's own
disclosed cadence and avoiding daily whipsaw on a lower-frequency signal.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: this strategy needs TWO separate price series (the underlying to
trade, plus lumber and gold reference series for the regime signal). Since
validation/grid_test.py's ``run_strategy_grid`` calls
``generate_returns_fn(price_df, **params)`` with a single price_df (the
traded symbol itself), lumber/gold reference data is fetched internally
here via data/loaders.py at generate_signals() call time, keyed off the
same date range as price_df.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_reference_series(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Fetch WOOD (lumber proxy) and GLD (gold) close series aligned to index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    wood = load_equity("WOOD", start, end, interval="1d")
    gld = load_equity("GLD", start, end, interval="1d")
    wood_close = (wood.set_index("timestamp") if "timestamp" in wood.columns else wood)["close"]
    gld_close = (gld.set_index("timestamp") if "timestamp" in gld.columns else gld)["close"]
    return wood_close, gld_close


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 65,
) -> pd.Series:
    """Return a {0,1} long/flat position series, weekly-rebalanced."""
    df = _prep(price_df)
    close = df["close"]

    wood_close, gld_close = _load_reference_series(close.index)
    wood_roc = wood_close.pct_change(roc_window)
    gld_roc = gld_close.pct_change(roc_window)

    wood_roc = wood_roc.reindex(close.index, method="ffill")
    gld_roc = gld_roc.reindex(close.index, method="ffill")

    risk_on = wood_roc > gld_roc

    # Weekly rebalance: signal is computed and LOCKED at each week's last
    # trading day, held constant through the following week (per source's
    # own disclosed cadence), rather than reacting daily.
    week_id = close.index.to_series().dt.isocalendar().week.astype(str) + "_" + \
        close.index.to_series().dt.isocalendar().year.astype(str)
    last_of_week = ~week_id.iloc[::-1].duplicated()
    last_of_week = last_of_week.iloc[::-1]
    weekly_signal = risk_on.where(last_of_week).ffill().fillna(False)
    # Shift by one day so the signal locked at week's close applies to the
    # FOLLOWING week's trading days, not retroactively to the lock day itself.
    weekly_signal_shifted = weekly_signal.shift(1).fillna(False)

    position = weekly_signal_shifted.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
