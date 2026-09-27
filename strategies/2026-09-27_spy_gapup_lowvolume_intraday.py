"""Strategy: SPY-style gap-up-after-low-volume intraday momentum.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://www.quantifiedstrategies.com/spy-volume-trading-strategy/ (free FAQ
disclosure -- full numeric rule table paywalled): "trading in the direction
of a 'big' gap up (more than 0.6%) on days following below-average volume
days can yield an average profit of 0.22% per trade" on SPY, backtested
2005-2024, intraday (buy the open, sell the close), 207 trades, ~55% win
rate, 9% max drawdown. Rationale (source's own): below-average volume
suggests reduced institutional hedging flow, so a subsequent large gap-up
is more likely a genuine catalyst-driven move that continues intraday
rather than mean-reverting. First strategy in this repo combining a
prior-day-below-average-volume filter with a next-day gap-up-magnitude
threshold on an intraday open-to-close basis (distinct from all prior
gap-continuation/gap-fade daily-close-to-close constructions, e.g.
2026-09-06-153 Gap-and-Go, 2026-09-20-083 Overnight Gap Dual
Classification).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)

Note: since this is an intraday (open-to-close) trade rather than an
overnight hold, generate_signals returns a {0,1} indicator of "trade this
day's session" rather than a persistent overnight position, and
generate_returns computes the open-to-close return on flagged days (0 on
all other days) to stay within this repo's daily-bar OHLCV contract.
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
    vol_avg_window: int = 20,
    vol_below_ratio: float = 1.0,
    min_gap_pct: float = 0.006,
) -> pd.Series:
    """Return a {0,1} indicator: 1 = trade today's open-to-close session
    (previous day's volume was below its own trailing average AND today's
    open gaps up from yesterday's close by at least min_gap_pct); 0 = flat.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"]

    vol_avg = volume.rolling(vol_avg_window).mean()
    prev_day_low_volume = (volume.shift(1) < (vol_avg.shift(1) * vol_below_ratio)).fillna(False)

    gap_pct = (open_ / close.shift(1)) - 1.0
    big_gap_up = (gap_pct >= min_gap_pct).fillna(False)

    signal = (prev_day_low_volume & big_gap_up).astype(int)
    return signal


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Open-to-close return on flagged days, 0 elsewhere (no transaction
    costs applied here). No lookahead: the signal at time t depends only on
    data available at/ before today's open (yesterday's close/volume, and
    today's own open vs yesterday's close), and the return realized is
    today's own open-to-close move -- consistent with an intraday buy-open,
    sell-close trade placed once the open print is known.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    intraday_ret = (close / open_) - 1.0

    signal = generate_signals(price_df, **kwargs)
    strat_ret = intraday_ret * signal
    return strat_ret.fillna(0.0)
