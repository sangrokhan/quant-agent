"""Strategy: MRAT (Moving Average Ratio) z-score threshold -- CRYPTO
LEVERAGE-CAP RESCUE of 2026-09-27-024's BTC/USDT near-miss.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
2026-09-27-024 (MRAT=MA(21)/MA(200) rolling-252d-z-score threshold, single-
symbol time-series adaptation of Avramov/Kaplanski/Subrahmanyam's
cross-sectional "Moving Average Distance" academic factor, per
https://aligrithm.com/moving-average-distance-the-technical-indicator-that-passed-the-cross-section/)
found BTC/USDT a concrete near-miss at entry_threshold=1.0/exit_threshold=0.3/
max_hold_days=60: Sharpe 1.012 (PASS), TC-survival 1.006 (PASS), walk-forward
1.0 (PASS), parameter sensitivity 0.083 (PASS) -- ONLY max-drawdown failed,
at 36.1% against the 25% threshold, driven by full 1.0x unscaled exposure on
crypto's higher realized volatility, not by signal quality. This entry
applies this repo's established leverage-cap-aware retune pattern (e.g.
2026-09-16_trix_sizing_sma_trend_crypto_lev.py): scale the {0,1} position
signal down to a fixed exposure level `leverage_cap` (<1.0) whenever long,
identical entry/exit logic otherwise, to bring MDD under 25% while
Sharpe/TC/walk-forward/param-sensitivity (leverage-scale-invariant up to a
point) should remain intact. Crypto-only recalibration -- no new external
source fetch needed; same formula and same source as 2026-09-27-024.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous exposure
        in [0, leverage_cap], NOT strictly {0,1} once leverage_cap != 1.0)
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
    leverage_cap: float = 0.6,
) -> pd.Series:
    """Return a continuous exposure series in [0, leverage_cap]."""
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

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False
            if exit_now or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            entry_now = bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False
            if entry_now:
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
