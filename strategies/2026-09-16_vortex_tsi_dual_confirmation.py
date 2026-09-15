"""Strategy: Vortex Indicator (VI+/VI-) crossover + TSI dual-confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-16-168):
Per Google AI-overview synthesis (Medium/Alexzap, Investopedia, TradingView
-- read via browser_exec fallback for the SERP; the underlying TSI/Vortex
formulas themselves are already public/disclosed in this repo's prior TSI
(2026-09-10-059/2026-09-14-096) and Vortex (2026-09-04-040/2026-09-13-095)
entries): a combined Vortex+TSI system requires BOTH indicators to agree
before entering -- VI+ crosses above VI- (trend-direction confirmation)
AND TSI crosses above its own signal line OR is already above zero
(momentum confirmation) -- filtering out false breakouts in sideways
markets that a single indicator alone would trade. Exit when either
confirmation reverses (VI- crosses back above VI+ OR TSI crosses below
its signal line), whichever comes first.

Novelty: this repo has 2 plain Vortex-crossover entries (2026-09-04-040
SMA-trend-filtered, 2026-09-06-091 ADX-filtered) and several TSI entries
(zero-line/signal-line crossover, continuous sizing dial variants), but
none combine Vortex direction confirmation with TSI momentum confirmation
as a dual AND-gate -- explicitly flagged as an untested angle in
2026-09-10-070's notes ("Vortex Indicator combos [saturated, 2+ prior
entries]" refers to Vortex+ADX and Vortex+SMA, not Vortex+TSI). Distinct
mechanism: two independently-constructed oscillators (Vortex from
high/low/close true-range ratios; TSI from double-smoothed price momentum)
must simultaneously confirm, rather than one oscillator plus a static
trend filter.

Signal logic
------------
- Vortex Indicator (window=vortex_window, standard True Range
  construction): VI+ crossing above VI- = trend confirmation.
- TSI (William Blau, r=tsi_r/s=tsi_s double-smoothed momentum, signal
  line = EMA(TSI, tsi_signal)): TSI > its own signal line = momentum
  confirmation.
- Entry (long): a fresh VI+/VI- bullish cross occurs AND TSI is already
  above its signal line at that bar (momentum already confirming, not
  waiting for a simultaneous fresh TSI cross too -- the source's own
  "TSI moves from negative to positive OR crosses above signal" framing
  is satisfied by requiring TSI > signal at the Vortex cross bar).
- Exit: VI- crosses back above VI+ (trend confirmation lost) OR TSI
  crosses below its own signal line (momentum confirmation lost) --
  whichever triggers first.
- Long-only, flat otherwise, per repo convention.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vortex(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    vm_plus = (high - low.shift(1)).abs()
    vm_minus = (low - high.shift(1)).abs()

    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    tr_sum = tr.rolling(window).sum()
    vi_plus = vm_plus.rolling(window).sum() / tr_sum
    vi_minus = vm_minus.rolling(window).sum() / tr_sum
    return vi_plus, vi_minus


def _tsi(close: pd.Series, r: int, s: int, signal_window: int) -> tuple[pd.Series, pd.Series]:
    price_diff = close.diff()
    double_smoothed_diff = price_diff.ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()
    double_smoothed_abs_diff = price_diff.abs().ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()
    tsi = 100 * (double_smoothed_diff / double_smoothed_abs_diff)
    signal = tsi.ewm(span=signal_window, adjust=False).mean()
    return tsi, signal


def generate_signals(
    price_df: pd.DataFrame,
    vortex_window: int = 14,
    tsi_r: int = 25,
    tsi_s: int = 13,
    tsi_signal: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vi_plus, vi_minus = _vortex(df, vortex_window)
    tsi, tsi_sig = _tsi(close, tsi_r, tsi_s, tsi_signal)

    vortex_bullish_cross = (vi_plus > vi_minus) & (vi_plus.shift(1) <= vi_minus.shift(1))
    vortex_bearish_cross = (vi_minus > vi_plus) & (vi_minus.shift(1) <= vi_plus.shift(1))
    tsi_bullish = tsi > tsi_sig
    tsi_bearish = tsi < tsi_sig

    entry = (vortex_bullish_cross & tsi_bullish).fillna(False)
    exit_signal = (vortex_bearish_cross | tsi_bearish).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
