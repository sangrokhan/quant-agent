"""Strategy: Overnight-only hold (prior close -> next open, flat intraday),
gated by 12-1 month (skip-month) momentum, per Lou/Polk/Skouras "A Tug of
War: Overnight Versus Intraday Expected Returns" (summarized at
https://alphaarchitect.com/overnight-momentum-vs-intraday-momentum/).

Hypothesis (knowledge_base id 2026-09-15-108):
Lou/Polk/Skouras decompose close-to-close returns into overnight and
intraday components and find that on cross-sectional momentum portfolios,
essentially ALL of the abnormal momentum return accrues overnight, while
other anomalies (value, size, etc.) accrue intraday. This repo already has
an unconditional overnight-hold strategy (2026-09-03-007, accepted) and an
overnight-hold gated by a generic SMA trend filter (2026-09-08-053,
accepted), plus a standalone full-day-hold 12-1 skip-month momentum
strategy (2026-09-09-032, rejected). This iteration combines the two ideas
directly as the paper's own finding suggests: hold ONLY overnight (flat
during the trading session, no intraday exposure at all), gated by whether
trailing 12-1 skip-month momentum (return from t-12mo to t-1mo, per
Jegadeesh-Titman convention) is positive -- testing whether the specific
momentum signal (rather than a simple price>SMA trend filter) is the
better overnight-hold gate, as implied by the paper's finding that momentum
premium (not generic trend) is the one that concentrates overnight.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position, held
    only overnight -- exposure represents "in position for that night's
    close-to-open return").
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


def _momentum_12_1(close: pd.Series, lookback_months: int, skip_months: int, bars_per_month: int) -> pd.Series:
    """12-1 skip-month momentum: return from (t - lookback_months) to
    (t - skip_months), expressed in bar units via bars_per_month.
    """
    lookback_bars = lookback_months * bars_per_month
    skip_bars = skip_months * bars_per_month
    far = close.shift(lookback_bars)
    near = close.shift(skip_bars)
    mom = (near / far) - 1.0
    return mom


def generate_signals(
    price_df: pd.DataFrame,
    lookback_months: int = 12,
    skip_months: int = 1,
    bars_per_month: int = 21,
    mom_threshold: float = 0.0,
) -> pd.Series:
    """Return a 0/1 series: 1 means "hold overnight tonight" (i.e. exposed
    to the close(t)->open(t+1) return), gated by positive 12-1 skip-month
    momentum measured as of close(t).
    """
    df = _prep(price_df)
    close = df["close"]

    mom = _momentum_12_1(close, lookback_months, skip_months, bars_per_month)
    hold_overnight = (mom > mom_threshold).fillna(False).astype(float)
    return hold_overnight


def generate_returns(
    price_df: pd.DataFrame,
    lookback_months: int = 12,
    skip_months: int = 1,
    bars_per_month: int = 21,
    mom_threshold: float = 0.0,
) -> pd.Series:
    """Daily strategy returns: only the close(t)->open(t+1) overnight
    return is captured, and only when momentum gate says to hold that
    night. No intraday (open->close) exposure is ever taken.
    """
    df = _prep(price_df)
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    # Overnight return realized at bar t+1's open, relative to bar t's close.
    overnight_ret = (open_.shift(-1) / close) - 1.0
    overnight_ret = overnight_ret.fillna(0.0)

    gate = generate_signals(
        price_df,
        lookback_months=lookback_months,
        skip_months=skip_months,
        bars_per_month=bars_per_month,
        mom_threshold=mom_threshold,
    )

    strat_ret = gate * overnight_ret
    # Shift by 1 to represent the return realized on bar t+1 (next day),
    # consistent with the rest of this repo's convention of positions
    # decided at close(t) producing a return attributed to the following bar.
    strat_ret = strat_ret.shift(1).fillna(0.0)
    return strat_ret
