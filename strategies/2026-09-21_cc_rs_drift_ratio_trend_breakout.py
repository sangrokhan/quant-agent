"""Strategy: Close-to-Close / Rogers-Satchell drift-ratio trend filter breakout.

Hypothesis (this iteration):
Per trendsandbreakouts.com's Rogers-Satchell Volatility article
(https://trendsandbreakouts.com/rogers-satchell-volatility, read via
browser_exec this iteration -- web_search backend intermittently returning
TLS/backend errors so browser fallback used for discovery): Rogers-Satchell
(RS) volatility is drift-independent (built purely from within-bar
open/high/low/close relationships), while standard close-to-close (CC)
realized volatility conflates directional drift with intrabar scatter. The
source's own disclosed practical rule: "Run Rogers-Satchell and
close-to-close vol over the same lookback. When close-to-close is
substantially higher than Rogers-Satchell, the difference is drift. The
stock is trending... That ratio by itself is a useful trend filter without
requiring any moving averages or momentum oscillators."

This strategy operationalizes that ratio (CC_vol / RS_vol) directly as a
standalone trend-detection gate for a simple breakout signal: go long when
the ratio exceeds a threshold (trending regime, per source) AND price makes
a new `breakout_window`-day high; exit when the ratio drops back toward 1.0
(range-bound reversion) or a max-hold time-stop. This is distinct from the
already-tested Rogers-Satchell/Parkinson/Garman-Klass/Yang-Zhang entries in
this repo (2026-09-17-050/051/052/058, 2026-09-20-094), all of which used a
single OHLC vol estimator as an INVERSE-VOL-TARGETING SIZING denominator on
top of a plain SMA trend gate -- none of them compared two DIFFERENT vol
estimators against each other as a ratio-based, indicator-free trend
detector, which is the source's own specific novel claim being tested here.

Signal logic
------------
- CC realized vol: rolling std of daily log returns over `vol_window`,
  annualized.
- RS realized vol: rolling mean of
      ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O)
  over `vol_window` bars, sqrt'd and annualized (each bar's contribution is
  guaranteed non-negative per the source, so no clipping needed).
- drift_ratio = CC_vol / RS_vol (>1 => trending per source's own framing).
- Entry (long): drift_ratio >= ratio_threshold AND close is a new
  `breakout_window`-day high (confirms the trend direction is up, since the
  ratio alone is non-directional).
- Exit: drift_ratio falls back below exit_ratio (regime reverts to
  range-bound, source's own "when the two converge, the stock is
  range-bound" signal), OR a max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals(price_df, **params) -> pd.Series {0,1};
generate_returns(price_df, **params) -> pd.Series of daily strategy returns.
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


def _rogers_satchell_var(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    # Guard against zero/negative prices producing invalid logs.
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    return pd.Series(term.values, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    breakout_window: int = 20,
    ratio_threshold: float = 1.5,
    exit_ratio: float = 1.1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    log_ret = np.log(close / close.shift(1))
    cc_var = log_ret.rolling(vol_window).var()
    cc_vol = np.sqrt(cc_var * 252)

    rs_term = _rogers_satchell_var(df)
    rs_var = rs_term.rolling(vol_window).mean().clip(lower=1e-12)
    rs_vol = np.sqrt(rs_var * 252)

    drift_ratio = (cc_vol / rs_vol).replace([np.inf, -np.inf], np.nan)

    rolling_high = close.rolling(breakout_window).max()
    new_high = close >= rolling_high

    entry = (drift_ratio >= ratio_threshold) & new_high
    exit_revert = drift_ratio <= exit_ratio

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.values
    exit_vals = exit_revert.values

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            ev = exit_vals[i] if not pd.isna(exit_vals[i]) else False
            if bool(ev) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            ent = entry_vals[i] if not pd.isna(entry_vals[i]) else False
            if bool(ent):
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
