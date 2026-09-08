"""Strategy: Jump-Weighted Momentum (magnitude-weighted formation returns).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per Beckmeyer & Wiedemann, "All Days Are Not Created Equal: Understanding
Momentum by Learning to Weight Past Returns" (Journal of Banking & Finance,
2025), https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5702162
(summarized via Google AI overview / ScienceDirect abstract, SSRN itself
blocked by Cloudflare bot check): standard 12-1 momentum equal-weights
every daily return in the formation window, but the paper's learned
"Characteristic-Managed Momentum" (CMM) model finds returns are highly
sparse -- on average just ~2 days receive ~30% of the total weight, and
~30 days account for over half the weight -- concentrated on days with
earnings announcements, market-wide jumps, or unusually large individual
price moves (informative-event days), while most other days are noise.
CMM reportedly achieves Sharpe 0.77 net of costs vs standard momentum's
much higher volatility (26.9% vs 12.6% annualized).

This repo has no earnings-date data and no cross-sectional universe (this
is a single-asset time-series repo), so we adapt the core finding --
"weight formation-period returns by their own realized magnitude
(jump-ness) rather than equally" -- as a single-asset TS momentum score:

Signal logic
------------
- Formation window: trailing `lookback_days` daily returns r_t.
- Jump weight for day t: w_t = |r_t| ** jump_power (jump_power > 1
  over-weights big-move days vs equal-weight momentum's jump_power=0;
  jump_power=0 recovers a simple sign-of-cumulative-return equal-weight
  momentum baseline).
- Jump-weighted momentum score: JWM_t = sum(w_t * r_t) / sum(w_t) over the
  lookback window (a weighted-average daily return, sign gives direction,
  magnitude-weighted like CMM's learned weights instead of a flat mean).
- Optional skip-most-recent-`skip_days` days (classic momentum convention,
  avoids the 1-month reversal effect the standard 12-1 formation already
  guards against).
- Long when JWM_t > 0, flat otherwise. Lagged 1 day (no look-ahead).

Distinct from every other momentum variant already in this repo: plain
12-month TSMOM (2026-09-03-012, equal-weight cumulative return), the
multiplicative reversal-tilt B=(1+r)*M (2026-09-08-144, rejected, still
equal-weights the base momentum calc, only multiplicatively tilts the
whole score by last month's return), and the multi-horizon vote
(2026-09-08-132, equal-weight per horizon then votes) -- none of them
reweight INDIVIDUAL DAYS within the formation window by realized |return|
magnitude the way this strategy does.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _jump_weighted_momentum(
    daily_ret: pd.Series,
    lookback_days: int,
    jump_power: float,
    skip_days: int,
) -> pd.Series:
    r = daily_ret.to_numpy(dtype=float)
    n = len(r)
    out = np.full(n, np.nan)
    min_periods = max(20, lookback_days // 3)

    for i in range(n):
        end = i - skip_days  # exclude the most recent skip_days returns
        if end < 0:
            continue
        start = max(0, end - lookback_days + 1)
        window = r[start : end + 1]
        window = window[~np.isnan(window)]
        if len(window) < min_periods:
            continue
        weights = np.abs(window) ** jump_power
        wsum = weights.sum()
        if wsum <= 0:
            continue
        out[i] = float((weights * window).sum() / wsum)

    return pd.Series(out, index=daily_ret.index)


def _simulate(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    jump_power: float = 2.0,
    skip_days: int = 5,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    jwm = _jump_weighted_momentum(daily_ret, lookback_days, jump_power, skip_days)

    raw_signal = (jwm > 0).fillna(False).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)

    strat_ret = position * daily_ret.fillna(0.0)

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    jump_power: float = 2.0,
    skip_days: int = 5,
) -> pd.Series:
    result = _simulate(price_df, lookback_days, jump_power, skip_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    jump_power: float = 2.0,
    skip_days: int = 5,
) -> pd.Series:
    result = _simulate(price_df, lookback_days, jump_power, skip_days)
    return result["returns"]
