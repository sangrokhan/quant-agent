"""Strategy: rolling-hedge-ratio cointegration z-score pairs trade,
expressed as a directional long/flat signal on the spread's mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Two economically-related instruments (same-sector equities, or two large-cap
crypto majors) share a long-run price relationship; when their price ratio
(spread, via a rolling OLS hedge ratio) diverges far from its recent mean
(as measured by a z-score), it tends to revert. Source:
https://www.quantifiedstrategies.com/pairs-trading-strategy/ (JPM/BAC
example) — spread = log(price_A) - beta*log(price_B) via linear regression
residuals; z-score of the spread crossing beyond a threshold (source uses
example thresholds of +/-1.2 to +/-2.3) signals a trading opportunity; exit
when the z-score reverts back toward zero.

Framework adaptation note: the repo's generate_signals/generate_returns
contract (see strategies/2026-09-03_bb_meanrev_qqq_volregime.py) takes a
single ``price_df`` (one symbol) plus **params, because validation/grid_test.py
drives one symbol at a time from data/loaders.py. Pairs trading inherently
needs a second instrument's data, so this strategy fetches the partner leg
internally (via data/loaders.py's load_equity/load_crypto) using the
``partner_symbol``/``asset_class`` params, keyed off ``price_df``'s own
date range. Only ONE directional leg is expressed as a position (long the
spread = long A / short B) rather than true market-neutral pairs trading, to
stay compatible with the existing 0/1 position-series convention used
throughout this repo.

Signal logic
------------
- hedge_window-day rolling OLS: spread_t = log(close_A) - beta_t * log(close_B),
  beta_t estimated over the trailing hedge_window bars (rolling regression).
- z-score of spread over trailing z_window bars (rolling mean/std).
- Entry (long the spread, i.e. long A / short B conceptually, expressed here
  as position=1 meaning "hold A only" for return-series purposes): z-score
  <= -entry_z (A is cheap relative to B, expect spread to revert upward).
- Exit: z-score reverts to >= -exit_z (spread has reverted most of the way
  back toward its mean), OR max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner(index: pd.DatetimeIndex, asset_class: str, partner_symbol: str) -> pd.Series:
    """Fetch the partner leg's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        partner_df = load_crypto(partner_symbol, start, end)
    else:
        partner_df = load_equity(partner_symbol, start, end)
    partner_df = _prep(partner_df)
    return partner_df["close"]


def _spread_zscore(
    price_df: pd.DataFrame,
    asset_class: str,
    partner_symbol: str,
    hedge_window: int,
    z_window: int,
) -> pd.Series:
    df = _prep(price_df)
    close_a = df["close"]
    close_b = _load_partner(df.index, asset_class, partner_symbol)
    close_b = close_b.reindex(close_a.index).ffill()

    log_a = np.log(close_a)
    log_b = np.log(close_b)

    # Rolling OLS hedge ratio beta_t = Cov(log_a, log_b) / Var(log_b) over
    # trailing hedge_window bars.
    cov = log_a.rolling(hedge_window).cov(log_b)
    var_b = log_b.rolling(hedge_window).var()
    beta = cov / var_b

    spread = log_a - beta * log_b
    spread_mean = spread.rolling(z_window).mean()
    spread_std = spread.rolling(z_window).std()
    z = (spread - spread_mean) / spread_std
    return z.replace([np.inf, -np.inf], np.nan)


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "BAC",
    hedge_window: int = 60,
    z_window: int = 20,
    entry_z: float = 1.5,
    exit_z: float = 0.3,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    z = _spread_zscore(price_df, asset_class, partner_symbol, hedge_window, z_window)
    z = z.reindex(df.index)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i, ts in enumerate(df.index):
        zt = z.iloc[i]
        if in_position:
            hold_days += 1
            if pd.isna(zt) or zt >= -exit_z or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if not pd.isna(zt) and zt <= -entry_z:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "BAC",
    hedge_window: int = 60,
    z_window: int = 20,
    entry_z: float = 1.5,
    exit_z: float = 0.3,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        partner_symbol=partner_symbol,
        hedge_window=hedge_window,
        z_window=z_window,
        entry_z=entry_z,
        exit_z=exit_z,
        max_hold_days=max_hold_days,
    )
    # Position taken at close t, held into return of t+1 (avoid lookahead).
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
