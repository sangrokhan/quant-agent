"""Strategy: Volume-Selectivity-Gated Crypto Weekend Hold (BTC/ETH).

Hypothesis (see knowledge_base id 2026-09-12-174):
Direct follow-up to already-rejected 2026-09-04-029 (unconditional
Friday-close-to-Monday-close crypto weekend hold, per QuantifiedStrategies.
com's paywalled "Weekend Effect In Bitcoin" strategy whose disclosed
aggregate stats -- BTC 103 trades avg 2.6%/trade 60% win rate but only
~10% TIME INVESTED, ETH 64 trades avg 2.2%/trade 53% win rate ~9% time
invested -- implied a highly SELECTIVE rule, not an unconditional weekly
hold). That entry's own rejection notes explicitly suggested: "gate
entries to only the lowest-liquidity/volume weekends... rather than an
unconditional weekly hold." This iteration implements exactly that
suggested fix, additionally grounded in independently-confirmed weekend
liquidity-drop context (Phemex: "Bitcoin weekend volume drops 20-40% vs
weekdays"; Investopedia: "Lower trading volumes on weekends can reduce
liquidity and increase risk").

Signal logic
------------
- Compute a rolling `vol_window`-day average of daily volume as of each
  Friday's close.
- Only take the Friday-close-to-Monday-close weekend hold when that
  Friday's own volume is BELOW `low_vol_percentile` of its own trailing
  `vol_window`-day distribution (i.e. only the quietest, most illiquid
  weekends -- directly implementing the ~9-10% selectivity the source's
  own aggregate stats imply, rather than every single week).
- Flat all other days (Monday through Thursday, and any Friday that
  doesn't meet the low-volume gate).

First volume-selectivity-gated crypto weekend-hold strategy in this repo,
directly distinct from the unconditional version (2026-09-04-029,
rejected, ~43% time invested with no selectivity filter) via the explicit
volume-percentile entry gate.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    low_vol_percentile: float = 0.25,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Works on either daily or intraday (e.g. hourly, as this repo's crypto
    loader provides) bars. Each bar's own day-of-week is used directly;
    daily volume is approximated as the rolling `vol_window`-BAR average
    (not calendar-day average) of the bar's own volume, so the same
    parameter values are directly comparable whether applied to daily
    equity bars or hourly crypto bars (both loaders are handled uniformly
    by the grid test's generic vol-regime split, so this strategy avoids
    hardcoding a daily-only resample).

    Long on any bar that falls on Friday, Saturday, or Sunday, but ONLY if
    the entry bar's own volume is below the `low_vol_percentile` quantile
    of its trailing `vol_window`-bar distribution (the "quietest, most
    illiquid weekend" selectivity gate) at the START of that weekend (the
    first Friday bar); once a weekend qualifies, hold through Saturday and
    Sunday bars unconditionally; flat Monday-Thursday.
    """
    df = _prep(price_df)
    volume = df["volume"]
    weekdays = pd.Series(df.index.dayofweek, index=df.index)  # Mon=0 ... Sun=6

    rolling_quantile = volume.rolling(vol_window).quantile(low_vol_percentile)
    is_low_vol = (volume <= rolling_quantile).fillna(False)

    is_friday = weekdays == 4
    qualifying_friday = (is_friday & is_low_vol).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    n = len(df)
    holding = False

    for i in range(n):
        wd = weekdays.iloc[i]
        if wd == 4:
            if bool(qualifying_friday.iloc[i]):
                holding = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 1 if holding else 0
        elif wd in (5, 6):
            position.iloc[i] = 1 if holding else 0
        else:
            # Monday-Thursday: exit/stay flat, reset holding state.
            holding = False
            position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    low_vol_percentile: float = 0.25,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        vol_window=vol_window,
        low_vol_percentile=low_vol_percentile,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
