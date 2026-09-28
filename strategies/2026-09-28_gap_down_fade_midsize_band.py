"""Strategy: Overnight gap-down fade, gated to a MID-SIZE gap band (not just
a minimum threshold) -- a direct retune of this repo's prior near-miss
2026-09-03-010, informed by pomegra.io's gap-size / fill-probability
breakdown.

Hypothesis
----------
This repo already tested (and rejected, id=2026-09-03-010) a plain
gap-down-fade with only a MINIMUM gap-size threshold: buy the open after
any gap down beyond `gap_threshold`, sell at the close. That failed mainly
on transaction-cost survival (net Sharpe went negative) and parameter
sensitivity (edge unstable across nearby thresholds) -- it fired on too
many small, noise-dominated gaps AND on very large gaps that (per
pomegra.io's "Overnight Gap Trading Strategy" wiki page, read via
browser_exec after web_search DDGS backend returned nothing for two related
queries this iteration) are "real" repricings that rarely fill: "Gaps
larger than 5% fill only 30-50% of the time (the gap is real, not
temporary)... Gaps of 1-3% fill 60-80% of the time (these are often
overreactions)."

This variant directly addresses that prior rejection by adding an UPPER
bound alongside the existing lower bound, restricting entries to a mid-size
gap-down BAND (`gap_min_threshold` to `gap_max_threshold`) where the source
claims fill probability is highest -- explicitly excluding both the tiny
noise-dominated gaps (too small to survive transaction costs, per the prior
rejection) and the large "real repricing" gaps (which the source says
rarely fill and would be fighting a genuine information event). Long-only,
same open-to-close intraday-only holding window as the prior attempt for a
clean, controlled comparison.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} per-day
        intraday participation flag, not a persistent multi-day position)
    generate_returns(price_df, **params) -> pd.Series
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
    gap_min_threshold: float = 0.01,
    gap_max_threshold: float = 0.03,
) -> pd.Series:
    """Return a {0,1} per-day intraday-session participation flag.

    1 means "buy at today's open, sell at today's close" (fading a
    mid-size gap down, band-gated: gap_min_threshold <= |gap| <=
    gap_max_threshold).
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    prev_close = close.shift(1)

    gap = open_ / prev_close - 1.0
    gap_down_magnitude = -gap  # positive number for gap-downs

    qualifies = (gap_down_magnitude >= gap_min_threshold) & (
        gap_down_magnitude <= gap_max_threshold
    )

    signal = qualifies.fillna(False).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    gap_min_threshold: float = 0.01,
    gap_max_threshold: float = 0.03,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs).

    Each qualifying day contributes the open-to-close return; non-qualifying
    days contribute zero (flat, no overnight exposure).
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    signal = generate_signals(
        price_df,
        gap_min_threshold=gap_min_threshold,
        gap_max_threshold=gap_max_threshold,
    )

    intraday_return = (close / open_) - 1.0
    strat_returns = intraday_return * signal
    return strat_returns.fillna(0.0)
