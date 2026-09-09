"""Strategy: Consistent Momentum (two-window consistency), longer formation
window + min_hold_days turnover gate -- direct follow-up fix for this cron
trigger's own rejected 2026-09-09-107 (Sharpe fail + decisive
transaction-cost-survival fail from excessive daily-rebalance turnover).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
2026-09-09-107's own rejection notes diagnosed the failure mode precisely:
"lengthen lookback_days further (toward the source's true ~126-day/6-month
formation window) and add an explicit min_hold_days gate to cut turnover
before re-testing TC-survival, since walk-forward/param-sensitivity
already look solid." This entry does exactly that: widens the
consistency-window length toward Quantpedia's actual 6-month (~126
trading day) formation period, and adds a min_hold_days gate that
suppresses EXIT signals (position drops from consistent to inconsistent)
for the first min_hold_days bars after entry -- the same "suppress
early exits to cut trade count" fix pattern already proven in this repo
(Klinger Volume Oscillator 2026-09-04-085, ZLEMA 2026-09-06-171,
Accelerator Oscillator 2026-09-06-174), identical entry/consistency logic
otherwise unchanged so any improvement is attributable to these two
turnover-reduction changes alone.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    lookback_days: int = 126,
    min_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Consistent-winner state: trailing `lookback_days` return is positive
    AND the trailing return over the PRIOR (non-overlapping) window of the
    same length is also positive. Once entered, exit signals (state
    flipping to inconsistent) are ignored for the first `min_hold_days`
    bars after entry, cutting turnover from noisy near-boundary flips.
    """
    df = _prep(price_df)
    close = df["close"]

    recent_window_ret = close / close.shift(lookback_days) - 1.0
    prior_window_ret = close.shift(lookback_days) / close.shift(2 * lookback_days) - 1.0

    consistent_winner = (recent_window_ret > 0) & (prior_window_ret > 0)
    raw_signal = consistent_winner.fillna(False).to_numpy()

    idx_list = close.index
    pos_arr = [0] * len(idx_list)
    in_position = False
    entry_idx = -1

    for i in range(len(idx_list)):
        if not in_position:
            if raw_signal[i]:
                in_position = True
                entry_idx = i
                pos_arr[i] = 1
        else:
            held = i - entry_idx
            if held < min_hold_days:
                # Suppress exit signal during the minimum hold window.
                pos_arr[i] = 1
            elif raw_signal[i]:
                pos_arr[i] = 1
            else:
                in_position = False
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=idx_list, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 126,
    min_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df, lookback_days=lookback_days, min_hold_days=min_hold_days
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
