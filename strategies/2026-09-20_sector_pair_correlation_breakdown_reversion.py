"""Strategy: sector-pair rolling-correlation breakdown -> lagging-leg reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per trendsandbreakouts.com's "Correlation Breakdown Trading" article
(https://trendsandbreakouts.com/correlation-breakdown-trading), two
same-sector ETFs that normally track each other closely (e.g. XLF
financials vs XLI industrials) occasionally decouple: their rolling
60-day Pearson correlation of daily returns drops to a statistically
unusual z-score (<= -2.0 vs. its own trailing 252-day mean/std) while
both legs keep trading. The source's own worked example and "Setup one:
the reversion trade" claims the lagging leg tends to catch back up when
the breakdown is a sector-specific shock rather than a macro regime
change; since this repo's strategy interface takes a single price_df
and returns a single long-only return series (no shorting
infrastructure per SAFETY.md), we approximate this as: go long the
PRIMARY leg (e.g. XLF) whenever the XLF/XLI 60-day rolling correlation
z-score is unusually low (breakdown detected) AND XLF's own trailing
short-term return has underperformed XLI's (XLF is "the lagging leg" in
that window) -- i.e. buying the leg that lagged going into the
breakdown, betting on a catch-up reversion. Exit when the correlation
z-score reverts back toward zero (regime normalizes) or after a
max-hold time-stop (avoid indefinite holds through a structural/macro
break, per the source's own warning that "some breakdowns are
permanent").

This is the first correlation-BREAKDOWN (z-scored departure from a
pair's own long-run correlation regime) strategy in this repo -- distinct
from existing "rolling correlation as a REGIME LEVEL filter" entries
(2026-09-10-032 SPY/TLT correlation threshold gate, 2026-09-16-119/120
CTI price-vs-linear-trend correlation) and from existing cross-asset
Z-SCORE SPREAD/RATIO pairs trades (2026-09-04-083 ETH/BTC, 2026-09-08-082
BTC/gold, 2026-09-08-074 V/MA) which z-score the LEVEL of a price ratio
or spread, not the z-score of a rolling CORRELATION statistic itself.

Signal logic
------------
- corr = rolling Pearson correlation (corr_window, default 60d) of daily
  log returns between the primary symbol (price_df, e.g. XLF) and a
  fixed secondary sector-ETF leg (fetched internally via data/loaders.py,
  e.g. XLI) for equities, or a fixed pair for crypto (default ETH vs BTC,
  since this repo's crypto universe is thin -- treated as a same-asset-
  class "sector" analogue).
- corr_mean / corr_std = rolling mean/std of `corr` over a trailing
  z_lookback window (default 252d, per source's own z-score recipe).
- z = (corr - corr_mean) / corr_std.
- lag_window-day cumulative return of primary vs. secondary determines
  which leg is "lagging" (primary underperforming secondary over the
  trailing lag_window).
- Entry (long primary leg): z <= -z_entry (breakdown detected) AND
  primary is the lagging leg (primary's trailing lag_window return <
  secondary's).
- Exit: z reverts to >= z_exit (regime normalizing, source's own
  reversion-thesis condition), OR max_hold_days elapses (time-stop,
  guards against the source's own warning that some breakdowns are
  structural/permanent, not tradeable reversions).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        price_df is the PRIMARY leg's OHLCV frame (e.g. XLF for equity,
        ETH/USDT for crypto); the secondary leg is fetched internally.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_secondary_series(index: pd.Index, secondary_symbol: str, asset_class: str,
                           start=None, end=None) -> pd.Series:
    """Fetch the secondary leg's close series aligned to `index`, via data/loaders.py."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)

    if asset_class == "crypto":
        sec_df = load_crypto(secondary_symbol, start=start, end=end, interval="1d")
    else:
        sec_df = load_equity(secondary_symbol, start=start, end=end)
    sec_df = _prep(sec_df)
    return sec_df["close"].reindex(index).ffill()


def _compute_frame(
    price_df: pd.DataFrame,
    secondary_symbol: str,
    asset_class: str,
    corr_window: int,
    z_lookback: int,
    lag_window: int,
) -> pd.DataFrame:
    df = _prep(price_df)
    close_p = df["close"]
    close_s = _get_secondary_series(df.index, secondary_symbol, asset_class)

    log_ret_p = np.log(close_p / close_p.shift(1))
    log_ret_s = np.log(close_s / close_s.shift(1))

    corr = log_ret_p.rolling(corr_window).corr(log_ret_s)
    corr_mean = corr.rolling(z_lookback, min_periods=max(20, corr_window)).mean()
    corr_std = corr.rolling(z_lookback, min_periods=max(20, corr_window)).std()
    z = (corr - corr_mean) / corr_std

    lag_ret_p = close_p.pct_change(lag_window)
    lag_ret_s = close_s.pct_change(lag_window)
    primary_lagging = lag_ret_p < lag_ret_s

    out = pd.DataFrame({
        "close": close_p,
        "z": z,
        "primary_lagging": primary_lagging,
    })
    return out


def generate_signals(
    price_df: pd.DataFrame,
    secondary_symbol: str = "XLI",
    asset_class: str = "equity",
    corr_window: int = 60,
    z_lookback: int = 252,
    lag_window: int = 15,
    z_entry: float = 2.0,
    z_exit: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long primary leg only)."""
    frame = _compute_frame(price_df, secondary_symbol, asset_class, corr_window, z_lookback, lag_window)
    z = frame["z"]
    primary_lagging = frame["primary_lagging"]

    entry = (z <= -z_entry) & primary_lagging.fillna(False)

    n = len(frame)
    position = pd.Series(0, index=frame.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        zi = z.iloc[i]
        if in_pos:
            hold_count += 1
            reverted = bool(zi >= -z_exit) if pd.notna(zi) else False
            if reverted or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    secondary_symbol: str = "XLI",
    asset_class: str = "equity",
    corr_window: int = 60,
    z_lookback: int = 252,
    lag_window: int = 15,
    z_entry: float = 2.0,
    z_exit: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (long-only primary leg)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        secondary_symbol=secondary_symbol,
        asset_class=asset_class,
        corr_window=corr_window,
        z_lookback=z_lookback,
        lag_window=lag_window,
        z_entry=z_entry,
        z_exit=z_exit,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
