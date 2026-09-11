"""Strategy: 1D Kalman-filter level vs. short SMA mean-reversion crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-112):
Per quantifiedstrategies.com's "Kalman Filter Trading Strategy" article
(https://www.quantifiedstrategies.com/kalman-filter-trading-strategy/),
a simple 1D Kalman filter on closing price produces a smooth latent "fair
value" estimate. Their disclosed rule: go LONG when the short (5-day) SMA
of close crosses UNDER the Kalman-filtered level (price has dipped below
its smoothed estimate -> short-term overshoot), and go FLAT/exit when the
short SMA crosses back ABOVE the Kalman level (price has mean-reverted).
This is a mean-reversion construction, explicitly distinct from the
already-tested Kalman strategies in this repo:
  - 2026-09-05-056 (dual fast/slow Kalman percentile-breakout, REJECTED,
    all asset classes)
  - 2026-09-08-052 (single constant-velocity Kalman with slope-confirmed
    trend-following crossover, ACCEPTED but QQQ equity only)
Here we test whether the SIMPLER single-filter, no-slope, pure
level-vs-SMA MEAN-REVERSION variant (not trend-following) clears the bar,
and whether it generalizes better across asset classes / vol regimes than
its trend-following sibling.

Kalman filter construction
---------------------------
A minimal scalar random-walk-plus-noise Kalman filter on the close price:
  state transition: level_t = level_{t-1} (random walk)
  observation: close_t = level_t + noise
  process variance Q (kalman_q) and observation variance R (kalman_r) are
  the two tunable smoothing parameters -- higher Q/R ratio -> filter tracks
  price more closely (less smoothing); lower ratio -> smoother/laggier.

Signal logic
------------
- kalman_level = recursive Kalman-filtered estimate of close.
- short_sma = rolling mean of close over `sma_window` days.
- Entry (long): short_sma crosses from >= kalman_level to < kalman_level
  (short SMA dips below the smoothed fair-value estimate).
- Exit: short_sma crosses back above kalman_level, OR a max holding period
  of `max_hold_days` trading days is reached (avoid indefinite holds if the
  crossover doesn't resolve).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept all tunable parameters as keyword args per RESEARCH_LOOP.md
Step 5's contract.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _kalman_filter(series: pd.Series, kalman_q: float, kalman_r: float) -> pd.Series:
    """Minimal scalar random-walk Kalman filter (level-only state)."""
    values = series.values
    n = len(values)
    est = [0.0] * n
    if n == 0:
        return pd.Series(est, index=series.index, dtype=float)

    x_hat = values[0]  # initial state estimate = first observed price
    p = 1.0  # initial estimate error covariance
    est[0] = x_hat
    for i in range(1, n):
        # Prediction step (random walk: state doesn't change)
        x_hat_minus = x_hat
        p_minus = p + kalman_q

        # Update step
        z = values[i]
        if z != z:  # NaN guard
            est[i] = x_hat_minus
            x_hat, p = x_hat_minus, p_minus
            continue
        k_gain = p_minus / (p_minus + kalman_r)
        x_hat = x_hat_minus + k_gain * (z - x_hat_minus)
        p = (1 - k_gain) * p_minus
        est[i] = x_hat

    return pd.Series(est, index=series.index, dtype=float)


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 5,
    kalman_q: float = 0.01,
    kalman_r: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kalman_level = _kalman_filter(close, kalman_q=kalman_q, kalman_r=kalman_r)
    short_sma = close.rolling(sma_window).mean()

    below = short_sma < kalman_level
    below_prev = below.shift(1).fillna(False)
    entry = below & (~below_prev)  # SMA crosses under the Kalman level
    exit_cross = (~below) & below_prev  # SMA crosses back above

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    # Shift by 1 day: yesterday's signal determines today's return exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
