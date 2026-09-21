"""Strategy: UNG/USO (natural gas vs. crude oil ETF) log-spread z-score
mean-reversion pairs trade.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-036):
Per investingwhisperer.com's "THE NATGAS VS. OIL TRADE LONG UNG-NYSE / SHORT
USO-NYSE" (https://investingwhisperer.com/the-natgas-vs-oil-trade-long-ung-nyse-short-uso-nyse/,
read via browser_exec Google SERP fallback -- web_search DDGS backend TLS-erroring
on this iteration's queries): the author's discretionary thesis is that
natural gas and crude oil, while both energy commodities, decouple during
periods of extreme relative pessimism on one leg (there, natgas futures
curve backwardation making the market "too bearish on natural gas" vs
crude), and a long-natgas/short-oil pair captures the eventual convergence.
This repo has no natgas-futures-curve/backwardation data source, so we
mechanically operationalize the same "relative extreme -> reversion" idea
using the two ETFs' own price history: z-score the log(UNG/USO) ratio
against its own rolling mean/std, and take the long-UNG leg of the pair
(this repo has no short-selling infrastructure -- see
strategies/2026-09-04_eth_btc_spread_zscore_pairs.py for the identical
single-leg-approximation pattern used for the ETH/BTC pairs trade) when the
ratio is unusually LOW (natgas cheap vs oil, i.e. the "too bearish on
natgas" condition), exiting on reversion back toward the rolling mean.

Distinct from all prior single-symbol UNG/USO strategies in this repo:
- 2026-09-13-012 (UNG autumn/winter seasonal calendar window, no oil leg,
  rejected on roll-decay).
- 2026-09-10-029 (XLE trend-following gated by USO's own momentum, a
  trend-confirmation gate, not a spread/ratio mean-reversion construction).
- 2026-09-09-054 (USO calendar-seasonality window, no natgas leg).
None of these compute a cross-asset UNG/USO ratio or z-score it -- this is
the first UNG/USO pairs-style spread strategy in this repo, following the
same log-spread z-score template validated for ETH/BTC (2026-09-04-083,
itself rejected, but the mechanical construction/interface is reused here
on a fundamentally different asset pair with a different qualitative
economic rationale: storage-cycle/backwardation-driven commodity
convergence rather than crypto cointegration).

Signal logic
------------
- spread = log(close_UNG) - log(close_USO)
- rolling_mean/std of spread over `window` days -> z-score
- Entry (long UNG leg only, no short-USO leg -- see rationale above):
  z < -entry_z (UNG unusually cheap relative to USO)
- Exit: z reverts to >= exit_z, OR |z| grows beyond stop_z (further
  divergence, stop-loss), OR max_hold_days elapses.
- Returns are UNG's own daily returns while the position is on (a
  long-only single-leg approximation, NOT market-neutral like a genuine
  pairs trade -- same documented simplification as the ETH/BTC strategy).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        price_df here is expected to be the UNG OHLCV frame; the USO leg
        is fetched internally via data/loaders.py.
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


def _get_uso_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch USO close series aligned to the given index, via data/loaders.py."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)
    uso_df = load_equity("USO", start=start, end=end)
    uso_df = _prep(uso_df)
    return uso_df["close"].reindex(index).ffill()


def _compute_z(price_df: pd.DataFrame, window: int) -> pd.Series:
    df = _prep(price_df)
    close_ung = df["close"]
    close_uso = _get_uso_series(df.index)
    spread = np.log(close_ung) - np.log(close_uso)
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
    """Return a {0,1} long/flat position series (long-UNG-leg approximation)."""
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
    """Return the strategy's daily return series (long-only UNG leg, no shorting USO)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, window=window, entry_z=entry_z, exit_z=exit_z, stop_z=stop_z, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
