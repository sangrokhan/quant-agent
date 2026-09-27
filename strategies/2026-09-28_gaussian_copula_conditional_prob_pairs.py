"""Strategy: Gaussian-copula conditional-probability pairs trade.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Hudson & Thames' "Copula for Pairs Trading: A Unified Overview of Common
Strategies" (https://hudsonthames.org/copula-for-pairs-trading-overview-of-
common-strategies/, read via browser_exec after web_extract's ddgs backend
could not extract the page). This repo has 20+ prior pairs-trading entries
(spread/z-score, rolling-OLS+ADF, Kalman dynamic hedge ratio) but ZERO prior
copula-based entries (0 hits for "copula" in strategies_index.jsonl before
this run) -- copula-based pairs trading is a structurally distinct family:
instead of building one combined spread series and z-scoring it, a copula
models the joint dependence structure of the TWO legs' RETURNS directly and
generates signals from each leg's own conditional CDF (conditional
probability), independently for each leg. This is "Strategy 1: Simple
Thresholds" from the source, adapted to use RETURNS instead of raw prices
(the source's own "Concern 1" flags raw non-stationary prices as
problematic for a copula fit; returns are much closer to the i.i.d.
assumption copulas need) and to work within this repo's rolling-window,
no-look-ahead, single-return-series constraints:

  1. Fit a bivariate GAUSSIAN COPULA (parameterized by a single correlation
     rho) on a trailing rolling window of standardized daily log-returns for
     both legs, refit every `refit_step` bars (a full copula fit every bar
     is unnecessary compute for a slow-moving correlation estimate and
     mirrors this repo's existing rolling-ADF-pairs precedent of stepped
     refitting, see strategies/2026-09-26_eth_btc_rolling_ols_adf_pairs.py).
  2. Convert each leg's trailing-window return to an empirical-CDF quantile
     u1, u2 in (0,1) using the SAME trailing window (rank-based, no
     look-ahead: today's rank is computed only against the window ending
     yesterday, i.e. window is shifted by 1).
  3. Compute the conditional probability under the fitted Gaussian copula:
        C_2|1(u2|u1) = Phi( (Phi^-1(u2) - rho*Phi^-1(u1)) / sqrt(1-rho^2) )
     This is the standard Gaussian-copula conditional CDF formula (closed
     form, no numerical integration needed) -- gives P(leg-2's return is
     "small" | leg-1's return quantile).
  4. Per the source's own AND-open/OR-exit recommendation ("Based on our
     tests, we found using AND for opening, OR for exiting on average
     captures better trading opportunities"):
       Open (long price_df's own leg, "leg A"): C_2|1(u2|u1) > b_up AND
       u1 < b_lo (leg A's own quantile is low/cheap AND leg B is
       conditionally overvalued given leg A -- mirrors the source's
       "stock 1 undervalued, stock 2 overvalued -> long the spread" rule,
       adapted to a single-return-series long-only approximation
       consistent with this repo's other pairs strategies).
       Exit (OR logic): either u1 crosses back above 0.5 OR the
       conditional probability C_2|1 crosses back below 0.5, OR a
       max_hold_days time-stop.
  5. Flat otherwise.

Pairs tested: QQQ/SPY (equity, both already used as a pair in this repo's
2026-09-04_spy_qqq_pairs_zscore.py, but with a structurally different
copula-based signal) and BTC/USDT paired against ETH/USDT (crypto).

Framework adaptation note: same partner-leg-fetch pattern as
strategies/2026-09-17_kalman_dynamic_hedge_pairs_meanrev.py -- price_df
carries the "A" leg's OHLCV; the "B" leg (partner_symbol) is fetched
internally via data/loaders.py.

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
    """Fetch the partner leg's close series over price_df's date range."""
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
    """Empirical-CDF quantile (in (0,1)) of today's return against the
    trailing `window` of PRIOR returns only (shifted by 1 -> no look-ahead).
    """
    prior = returns.shift(1)

    def _rank_last(arr: np.ndarray) -> float:
        # arr's last element is today's value already included in shift(1)
        # window construction below via rolling().apply; here we rank the
        # CURRENT (unshifted) value against the window of PRIOR values.
        return np.nan

    # Rank today's return within the window of the PRIOR `window` returns.
    n = len(returns)
    vals = returns.to_numpy()
    out = np.full(n, np.nan)
    for i in range(window, n):
        hist = vals[i - window:i]  # strictly prior to i
        if np.all(np.isfinite(hist)) and np.isfinite(vals[i]):
            # empirical CDF: fraction of history <= today's value
            out[i] = (np.sum(hist <= vals[i]) + 0.5) / (window + 1)
    return pd.Series(out, index=returns.index)


def _rolling_gaussian_copula_rho(u1: pd.Series, u2: pd.Series, window: int, step: int) -> pd.Series:
    """Rolling Gaussian-copula correlation rho, estimated on the normal-
    quantile-transformed (Phi^-1) trailing window of u1,u2, refit every
    `step` bars (forward-filled between) for tractability. Only uses data
    strictly prior to the current bar (shifted by 1)."""
    z1 = norm.ppf(u1.clip(1e-4, 1 - 1e-4))
    z2 = norm.ppf(u2.clip(1e-4, 1 - 1e-4))
    z1 = pd.Series(z1, index=u1.index)
    z2 = pd.Series(z2, index=u2.index)

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
    series = pd.Series(rho, index=z1.index)
    return series.ffill()


def _compute_signal_frame(
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

    u1 = _rolling_rank_uniform(ret_a, rank_window)
    u2 = _rolling_rank_uniform(ret_b, rank_window)

    rho = _rolling_gaussian_copula_rho(u1, u2, rank_window, rho_step)

    z1 = pd.Series(norm.ppf(u1.clip(1e-4, 1 - 1e-4)), index=u1.index)
    z2 = pd.Series(norm.ppf(u2.clip(1e-4, 1 - 1e-4)), index=u2.index)

    denom = np.sqrt(np.clip(1 - rho ** 2, 1e-6, None))
    cond_prob_2_given_1 = pd.Series(
        norm.cdf((z2 - rho * z1) / denom), index=u1.index
    )

    out = pd.DataFrame({"u1": u1, "cond_2_given_1": cond_prob_2_given_1}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "SPY",
    rank_window: int = 60,
    rho_step: int = 5,
    b_lo: float = 0.15,
    b_up: float = 0.85,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a 0/1 long/flat position series. Long price_df's own leg (A)
    when A is conditionally cheap (u1 < b_lo) AND B is conditionally
    overvalued given A (cond_2_given_1 > b_up). Exit (OR logic) when EITHER
    u1 crosses back above 0.5 OR cond_2_given_1 crosses back below 0.5, or
    a max_hold_days time-stop."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, asset_class, partner_symbol, rank_window, rho_step)
    u1 = sig["u1"]
    c21 = sig["cond_2_given_1"]

    n = len(df)
    u1_vals = u1.to_numpy()
    c21_vals = c21.to_numpy()
    pos_vals = np.zeros(n, dtype=int)

    in_pos = False
    hold_count = 0
    for i in range(n):
        u1i = u1_vals[i]
        c21i = c21_vals[i]
        valid = np.isfinite(u1i) and np.isfinite(c21i)
        if in_pos:
            hold_count += 1
            reverted = valid and (u1i >= 0.5 or c21i <= 0.5)
            if reverted or hold_count >= max_hold_days:
                in_pos = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if valid and (u1i < b_lo) and (c21i > b_up):
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
    b_lo: float = 0.15,
    b_up: float = 0.85,
    max_hold_days: int = 20,
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
        b_lo=b_lo,
        b_up=b_up,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
