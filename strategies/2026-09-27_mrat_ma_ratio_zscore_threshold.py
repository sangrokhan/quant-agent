"""Strategy: Moving-Average-Ratio (MRAT) trend-strength threshold, single-symbol
time-series adaptation of Avramov/Kaplanski/Subrahmanyam's cross-sectional
"Moving Average Distance" factor.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per https://aligrithm.com/moving-average-distance-the-technical-indicator-that-passed-the-cross-section/
(Ali H. Askar, Aligrithm, Sep 23 2026, summarizing Avramov, Kaplanski &
Subrahmanyam's academic paper, read via browser_exec fallback after
web_extract's ddgs backend cannot fetch page content): MRAT = MA(21) / MA(200)
(ratio of the 21-day to 200-day moving average of price) predicts future
returns cross-sectionally -- stocks in the top decile with MRAT > 1 + sigma
(sigma = cross-sectional std of MRAT that month) earn 9.05% annual alpha
(t=3.02), entirely on the LONG leg (short leg pays ~0%). The source's own
finding: a plain golden-cross/death-cross BINARY event dummy is dead
(t=1.17) -- what's alive is treating the ratio as a CONTINUOUS magnitude and
thresholding on how far it deviates from its OWN typical dispersion, not
merely whether the crossover fired.

This repo's single-symbol architecture cannot replicate the cross-sectional
ranking (would need a many-stock universe each month), so this adapts the
core mechanism to a single-asset TIME-SERIES threshold: compute MRAT's own
history, rolling-z-score it against its own trailing distribution (instead
of the paper's cross-sectional sigma), and go long only when the z-score
exceeds a long_threshold (analogous to the paper's "top decile AND >1+sigma"
double condition, here approximated by a single z-score cutoff on one
series). Exit when the z-score falls back below an exit_threshold (lower
than the entry threshold, to avoid immediately flip-flopping right at the
boundary) or a max_hold_days time-stop. Distinct from this repo's existing
golden-cross/death-cross BINARY MA-crossover strategies (which the source's
own t=1.17 finding says should be flat) and from other MA-ratio-style
regime filters (e.g. 2026-09-05-068 Growth/Value ETF ratio, a cross-ASSET
ratio not a same-asset dual-MA ratio).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    fast_window: int = 21,
    slow_window: int = 200,
    zscore_window: int = 252,
    entry_threshold: float = 1.0,
    exit_threshold: float = 0.3,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ma_fast = close.rolling(fast_window, min_periods=fast_window).mean()
    ma_slow = close.rolling(slow_window, min_periods=slow_window).mean()
    mrat = ma_fast / ma_slow

    mrat_mean = mrat.rolling(zscore_window, min_periods=zscore_window).mean()
    mrat_std = mrat.rolling(zscore_window, min_periods=zscore_window).std()
    zscore = (mrat - mrat_mean) / mrat_std.replace(0.0, pd.NA)

    entry = zscore > entry_threshold
    exit_signal = zscore < exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False
            if exit_now or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_now = bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False
            if entry_now:
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
