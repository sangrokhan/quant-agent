"""Strategy: Cumulative Mispricing Index (CMPI) copula pairs trade.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Hudson & Thames' "Copula for Pairs Trading: A Unified Overview of Common
Strategies" (https://hudsonthames.org/copula-for-pairs-trading-overview-of-
common-strategies/, Strategy 2 section, read via browser_exec after
web_extract's ddgs backend could not extract the page). Distinct from this
same cron trigger's earlier copula entry (2026-09-28-030, Strategy 1: simple
thresholds on PRICES, rejected) -- this is a structurally different signal
construction (Strategy 2: Cumulative Mispricing Index on RETURNS), citing
[Xie et al. 2014][Stubinger et al. 2016][Rad et al. 2016][da Silva et al.
2017] and genuinely novel for this repo (0 prior "mispricing index"/"CMPI"
hits in strategies_index.jsonl):

  1. Fit a bivariate Gaussian copula (rolling correlation rho, refit every
     `rho_step` bars, strictly on data prior to the current bar) on the
     trailing-window standardized daily log-returns of two legs, same
     copula-fitting machinery as 2026-09-28-030 but applied to a
     structurally different signal (CMPI, not a single-bar conditional
     probability against fixed thresholds).
  2. Daily Mispricing Index (MPI) for each leg: the copula's conditional
     probability of that leg's return given the other leg's return that
     day -- MPI_A,t = C_A|B(u_A,t | u_B,t), MPI_B,t = C_B|A(u_B,t | u_A,t).
  3. Cumulative Mispricing Index (CMPI, "Flags"): CMPI_t = CMPI_{t-1} +
     (MPI_t - 0.5) (subtract 0.5 so overvalued/undervalued reads as
     positive/negative, per the source's own construction -- this makes
     CMPI behave like a cumulative log-return-of-mispricing series).
  4. Trading logic: this iteration implements the Rad et al (2016)
     variation the source explicitly highlights as the best-performing
     documented variant ("suggested using AND for opening, OR for exiting,
     and no reset" -- "the performance of the copula approach is similar to
     ... distance and cointegration methods ... has better performance
     during market downturns"):
       Open long (price_df's own leg "A", the cheap leg): CMPI_A <=
       -cmpi_open_threshold AND CMPI_B >= +cmpi_open_threshold (A
       undervalued AND B overvalued, consistent AND-logic mirroring the
       source's dollar-neutral "short overvalued / buy undervalued" rule,
       reduced here to this repo's long-only single-return-series
       convention used by all its other pairs-trade entries).
       Exit (OR logic, NO reset before exit -- CMPI keeps accumulating
       while in position): CMPI_A returns to >= 0 (source's own "CMPI
       returns to 0" rule) OR CMPI_A reaches the stop-loss level
       (<= -cmpi_stop_threshold) OR a max_hold_days time-stop. CMPI is
       reset to 0 only AFTER a position closes (source's own "after trades
       are closed, both CMPI_A and CMPI_B are reset to 0" rule).
  5. Flat otherwise.

Pairs tested: same universe as 2026-09-28-030 -- QQQ/SPY (equity) and
BTC/USDT vs ETH/USDT (crypto).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.stats import norm


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner(index: pd.DatetimeIndex, asset_class: str, partner_symbol: str) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        partner_df = load_crypto(partner_symbol, start, end, interval="1d")
    else:
        partner_df = load_equity(partner_symbol, start, end)
    partner_df = _prep(partner_df)
    return partner_df["close"]


def _rolling_rank_uniform(returns: pd.Series, window: int) -> pd.Series:
    """Empirical-CDF quantile of today's return against the trailing
    `window` PRIOR returns only (no look-ahead)."""
    n = len(returns)
    vals = returns.to_numpy()
    out = np.full(n, np.nan)
    for i in range(window, n):
        hist = vals[i - window:i]
        if np.all(np.isfinite(hist)) and np.isfinite(vals[i]):
            out[i] = (np.sum(hist <= vals[i]) + 0.5) / (window + 1)
    return pd.Series(out, index=returns.index)


def _rolling_gaussian_copula_rho(u1: pd.Series, u2: pd.Series, window: int, step: int) -> pd.Series:
    z1 = pd.Series(norm.ppf(u1.clip(1e-4, 1 - 1e-4)), index=u1.index)
    z2 = pd.Series(norm.ppf(u2.clip(1e-4, 1 - 1e-4)), index=u2.index)

    n = len(z1)
    rho = np.full(n, np.nan)
    i = window
    while i < n:
        w1 = z1.iloc[i - window:i].to_numpy()
        w2 = z2.iloc[i - window:i].to_numpy()
        mask = np.isfinite(w1) & np.isfinite(w2)
        if mask.sum() > window // 2:
            r = np.corrcoef(w1[mask], w2[mask])[0, 1]
            rho[i] = np.clip(r, -0.98, 0.98)
        i += step
    return pd.Series(rho, index=z1.index).ffill()


def _compute_mpi_frame(
    price_df: pd.DataFrame,
    asset_class: str,
    partner_symbol: str,
    rank_window: int,
    rho_step: int,
) -> pd.DataFrame:
    df = _prep(price_df)
    close_a = df["close"]
    close_b = _load_partner(df.index, asset_class, partner_symbol)
    close_b = close_b.reindex(close_a.index).ffill()

    ret_a = np.log(close_a.replace(0, np.nan)).diff()
    ret_b = np.log(close_b.replace(0, np.nan)).diff()

    u_a = _rolling_rank_uniform(ret_a, rank_window)
    u_b = _rolling_rank_uniform(ret_b, rank_window)

    rho = _rolling_gaussian_copula_rho(u_a, u_b, rank_window, rho_step)

    z_a = pd.Series(norm.ppf(u_a.clip(1e-4, 1 - 1e-4)), index=u_a.index)
    z_b = pd.Series(norm.ppf(u_b.clip(1e-4, 1 - 1e-4)), index=u_b.index)
    denom = np.sqrt(np.clip(1 - rho ** 2, 1e-6, None))

    # MPI_A = C_A|B(u_A | u_B): conditional prob of A given B
    mpi_a = pd.Series(norm.cdf((z_a - rho * z_b) / denom), index=u_a.index)
    # MPI_B = C_B|A(u_B | u_A): conditional prob of B given A
    mpi_b = pd.Series(norm.cdf((z_b - rho * z_a) / denom), index=u_b.index)

    out = pd.DataFrame({"mpi_a": mpi_a, "mpi_b": mpi_b}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "SPY",
    rank_window: int = 60,
    rho_step: int = 5,
    cmpi_open_threshold: float = 3.0,
    cmpi_stop_threshold: float = 6.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a 0/1 long/flat position series -- Rad et al (2016) variation:
    AND-logic open, OR-logic exit, NO reset while in position (only reset
    after a position closes). Long price_df's own leg (A, the undervalued
    leg) when CMPI_A <= -cmpi_open_threshold AND CMPI_B >= +cmpi_open_threshold.
    """
    df = _prep(price_df)
    mpi = _compute_mpi_frame(df, asset_class, partner_symbol, rank_window, rho_step)
    mpi_a = mpi["mpi_a"].to_numpy()
    mpi_b = mpi["mpi_b"].to_numpy()

    n = len(df)
    pos_vals = np.zeros(n, dtype=int)

    cmpi_a = 0.0
    cmpi_b = 0.0
    in_pos = False
    hold_count = 0

    for i in range(n):
        ma = mpi_a[i]
        mb = mpi_b[i]
        valid = np.isfinite(ma) and np.isfinite(mb)
        if valid:
            cmpi_a += (ma - 0.5)
            cmpi_b += (mb - 0.5)

        if in_pos:
            hold_count += 1
            reverted = cmpi_a >= 0.0
            stopped = cmpi_a <= -cmpi_stop_threshold
            if reverted or stopped or hold_count >= max_hold_days:
                in_pos = False
                cmpi_a = 0.0
                cmpi_b = 0.0
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if valid and (cmpi_a <= -cmpi_open_threshold) and (cmpi_b >= cmpi_open_threshold):
                in_pos = True
                hold_count = 0
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0

    return pd.Series(pos_vals, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "SPY",
    rank_window: int = 60,
    rho_step: int = 5,
    cmpi_open_threshold: float = 3.0,
    cmpi_stop_threshold: float = 6.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's leg-A simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        asset_class=asset_class,
        partner_symbol=partner_symbol,
        rank_window=rank_window,
        rho_step=rho_step,
        cmpi_open_threshold=cmpi_open_threshold,
        cmpi_stop_threshold=cmpi_stop_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
