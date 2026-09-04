"""Strategy: ETH/BTC log-spread cointegration pairs trade (mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-083):
Per validatedstrategies.com's own (already-negative) writeup, ETH and BTC
prices are hypothesized to be cointegrated, so the log(ETH/BTC) spread is
mean-reverting: z-score the daily spread against a rolling mean/std,
enter a spread-reversion position (long ETH / short BTC) when z < -2,
exit when z reverts to 0, stop out at |z| >= 3.5. Distinct from every
other strategy in this repo -- it's the first CROSS-ASSET spread/pairs
strategy (single-leg strategies dominate this repo's knowledge base); the
source itself already backtested this exact rule over 2018-2026 and found
it decisively broken (not cointegrated per Engle-Granger/Johansen tests,
486-day spread half-life, catastrophic -93% drawdown in the 2021 ETH
re-pricing regime break, fails a placebo/permutation test). We reproduce
a version of it here on this repo's own data/validator stack rather than
just trusting the source's verdict, since our thresholds (Sharpe/MDD/TC)
differ from theirs (profit factor/placebo).

Signal logic
------------
- spread = log(close_eth) - log(close_btc)  (implicitly assumes a 1:1 log
  hedge ratio -- a simplification vs. a fitted cointegration beta, in
  keeping with this repo's single-price-series strategy interface)
- rolling_mean/std of spread over `window` days -> z-score
- Entry (long ETH leg only -- this repo has no short-selling
  infrastructure, so we approximate the "long the cheap leg" side of the
  pairs trade as a long-only position in ETH when the spread is
  unusually LOW, i.e. ETH cheap relative to BTC): z < -entry_z
- Exit: z reverts to >= exit_z (default 0), OR |z| grows beyond stop_z
  (stop-loss on further divergence), OR max_hold_days elapses.
- Returns are the ETH leg's own daily returns while the position is on
  (a long-only single-leg approximation of the full pairs trade, since
  this repo's generate_returns contract returns one return series, not a
  two-leg P&L; NOTE this deliberately does NOT hedge/short BTC, so it is
  NOT market-neutral like the source's real pairs trade -- documented
  here as a known simplification, see notes in the knowledge base entry).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        price_df here is expected to be the ETH/USDT OHLCV frame; the BTC
        leg is fetched internally via data/loaders.py.
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btc_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch BTC/USDT close series aligned to the given index, via data/loaders.py."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_crypto  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)
    btc_df = load_crypto("BTC/USDT", start=start, end=end)
    btc_df = _prep(btc_df)
    return btc_df["close"].reindex(index).ffill()


def _compute_z(price_df: pd.DataFrame, window: int) -> pd.Series:
    df = _prep(price_df)
    close_eth = df["close"]
    close_btc = _get_btc_series(df.index)
    spread = np.log(close_eth) - np.log(close_btc)
    rolling_mean = spread.rolling(window).mean()
    rolling_std = spread.rolling(window).std()
    z = (spread - rolling_mean) / rolling_std
    return z


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 30,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    stop_z: float = 3.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-ETH-leg approximation)."""
    df = _prep(price_df)
    z = _compute_z(df, window)
    z_prev = z.shift(1)
    entry_trigger = (z < -entry_z) & (z_prev >= -entry_z)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        zi = z.iloc[i]
        if in_pos:
            hold_count += 1
            reverted = (zi >= exit_z) if pd.notna(zi) else False
            stopped = (abs(zi) >= stop_z) if pd.notna(zi) else False
            if reverted or stopped or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 30,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    stop_z: float = 3.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (long-only ETH leg, no shorting BTC)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, window=window, entry_z=entry_z, exit_z=exit_z, stop_z=stop_z, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
