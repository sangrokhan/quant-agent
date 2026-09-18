"""Strategy: Ehlers/Ric Way Zero-Lag (Error-Correcting) EMA crossover.

Hypothesis (source: https://sacredtraders.com/zero-lag-well-almost-by-john-ehlers-and-ric-way/,
read via browser_exec; TASC article by John Ehlers and Ric Way):

An EMA has an inherent error term each bar: Price - EMA[1]. Feeding a
gain-scaled version of that error back into the filter produces an
"error-correcting" (EC) line that leads a standard EMA of the same
equivalent length, without the overshoot/whipsaw of naively removing all
lag. The source's own disclosed formula and trading rule:

    a  = 2 / (length + 1)                      (standard EMA smoothing factor)
    EC = a * (Price + Gain * (Price - EC[-1])) + (1 - a) * EC[-1]

where, each bar, `Gain` is searched over [-gain_limit/10, +gain_limit/10]
in steps of 0.1 to MINIMIZE |Price - EC| (the "least error" search the
source's EasyLanguage code performs). When EC is above the EMA, the source
says the market is in "bull mode"; below, "bear mode". The source's own
disclosed trading rule uses the EC/EMA crossover as entry/exit, but adds a
whipsaw filter: only take the crossover if the least-error magnitude at
that bar (as a percentage of price) exceeds a threshold `thresh_pct`
(source's own explicit fix for "a considerable number of undesirable
whipsaw trades" when EC and EMA sit nearly on top of each other). This is a
genuinely new indicator family for this repo -- zero prior Error-Correcting/
Zero-Lag-Ric-Way entries (distinct construction from all of this repo's many
prior Ehlers SuperSmoother/Roofing Filter/Reflex/Trendflex/Laguerre entries,
none of which use an error-feedback loop).

Signal logic
------------
- Compute EMA(length) as the baseline.
- Each bar, search Gain over the disclosed range to minimize |Price - EC|,
  producing the EC line and its associated least-error magnitude.
- Entry (long): EC crosses above EMA AND the least-error magnitude (as a
  fraction of price) exceeds `thresh_pct` (source's own whipsaw filter).
- Exit: EC crosses back below EMA (mirror condition), or `max_hold_days`
  time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _ec_ema(close: pd.Series, length: int, gain_limit: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the EC (error-corrected) line, EMA, and per-bar least-error
    magnitude (source's disclosed per-bar gain-search algorithm)."""
    n = len(close)
    prices = close.to_numpy(dtype=float)
    a = 2.0 / (length + 1.0)

    ema = np.full(n, np.nan)
    ec = np.full(n, np.nan)
    least_error = np.full(n, np.nan)

    gain_candidates = np.arange(-gain_limit / 10.0, gain_limit / 10.0 + 0.05, 0.1)

    for i in range(n):
        price = prices[i]
        if i == 0 or np.isnan(prices[i - 1]):
            ema[i] = price
            ec[i] = price
            least_error[i] = 0.0
            continue
        ema[i] = a * price + (1 - a) * ema[i - 1]

        ec_prev = ec[i - 1]
        candidates = a * (price + gain_candidates * (price - ec_prev)) + (1 - a) * ec_prev
        errors = np.abs(price - candidates)
        best_idx = np.argmin(errors)
        ec[i] = candidates[best_idx]
        least_error[i] = errors[best_idx]

    return ec, ema, least_error


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 32,
    gain_limit: float = 22.0,
    thresh_pct: float = 0.75,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ec, ema, least_error = _ec_ema(close, length=length, gain_limit=gain_limit)
    ec_s = pd.Series(ec, index=close.index)
    ema_s = pd.Series(ema, index=close.index)
    least_error_pct = pd.Series(least_error, index=close.index) / close.replace(0, np.nan) * 100.0

    bullish_cross = (ec_s > ema_s) & (ec_s.shift(1) <= ema_s.shift(1))
    bearish_cross = (ec_s < ema_s) & (ec_s.shift(1) >= ema_s.shift(1))
    strong_entry = bullish_cross & (least_error_pct.fillna(0) > thresh_pct)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    strong_entry_vals = strong_entry.fillna(False).to_numpy()
    bearish_exit_vals = bearish_cross.fillna(False).to_numpy()

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bearish_exit_vals[i] or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if strong_entry_vals[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
