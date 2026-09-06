"""Strategy: KST bullish divergence + signal-line cross + 200 EMA trend
filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-017):
Per https://theindicatorlab.com/reviews/kst-know-sure-thing/, source's own
disclosed "highest probability setup": (1) trend filter -- price above the
200 EMA for longs; (2) bullish divergence -- price makes a lower low while
KST makes a higher low; (3) KST crosses above its signal line -> long entry.
Source claims a 70% win rate on SPY with this combo since May. Exit: KST
crosses back below its signal line, or KST hits an extreme reading (>100 on
daily) -- the source's own stated exit conditions.

This is distinct from BOTH existing KST strategies in this repo:
- 2026-09-04_kst_signalline_cross.py (Pring classic ROC periods 10/15/20/30,
  signal-line cross while AT/BELOW zero, no divergence, no trend filter)
- 2026-09-06_kst_zero_cross_trendspider.py (TrendSpider period set 9/12/18/24,
  pure zero-line cross, no signal line, no divergence, no trend filter)
Neither uses divergence detection or an explicit 200 EMA trend gate; this
strategy adds both on top of the classic Pring KST/signal-line construction.

KST formula (standard, Martin Pring; same construction as
2026-09-04_kst_signalline_cross.py for direct comparability):
    ROC_i(n) = 100 * (close / close.shift(n) - 1)
    RCMA_i = SMA(ROC_i(roc_period_i), sma_period_i)
    KST = sum(weight_i * RCMA_i)
    signal = SMA(KST, signal_period)

Divergence detection: over a rolling `divergence_lookback` window, compare
the current bar's close/KST value against the window's local minimum
(swing low) of price -- if price registers a new N-bar low while KST is
ABOVE the KST value it had at that prior price low, that is a bullish
divergence flag valid for `divergence_valid_bars` bars going forward (a
divergence is a setup condition, not an instantaneous trigger -- the actual
entry trigger is the subsequent signal-line cross while the divergence flag
is still active).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _kst(close: pd.Series, signal_period: int = 9) -> tuple[pd.Series, pd.Series]:
    roc_periods = [10, 15, 20, 30]
    sma_periods = [10, 10, 10, 15]
    weights = [1, 2, 3, 4]

    rcma_sum = pd.Series(0.0, index=close.index)
    for roc_p, sma_p, w in zip(roc_periods, sma_periods, weights):
        roc = 100.0 * (close / close.shift(roc_p) - 1.0)
        rcma = roc.rolling(sma_p).mean()
        rcma_sum = rcma_sum + w * rcma

    signal = rcma_sum.rolling(signal_period).mean()
    return rcma_sum, signal


def _bullish_divergence_flag(
    close: pd.Series, kst: pd.Series, lookback: int, valid_bars: int
) -> pd.Series:
    """True on bars where a bullish divergence was recently confirmed
    (price N-bar low with KST higher than at the prior N-bar low), and
    remains True for `valid_bars` bars after confirmation."""
    n = len(close)
    close_vals = close.values
    kst_vals = kst.values
    flag = np.zeros(n, dtype=bool)

    # Track index of the most recent local price low within the lookback.
    rolling_min_idx = np.full(n, -1, dtype=int)
    for i in range(n):
        lo = max(0, i - lookback + 1)
        window = close_vals[lo : i + 1]
        if len(window) == 0 or np.all(np.isnan(window)):
            continue
        local_min_pos = np.nanargmin(window)
        rolling_min_idx[i] = lo + local_min_pos

    confirmed_until = -1
    prev_min_idx = -1
    for i in range(1, n):
        cur_min_idx = rolling_min_idx[i]
        # A "new low" event: current bar IS the rolling min and it's a fresh index
        if cur_min_idx == i and cur_min_idx != prev_min_idx:
            # compare against the min in the PRIOR lookback window (before current window)
            prior_start = max(0, i - 2 * lookback)
            prior_end = max(0, i - lookback)
            if prior_end > prior_start:
                prior_window = close_vals[prior_start:prior_end]
                if len(prior_window) > 0 and not np.all(np.isnan(prior_window)):
                    prior_min_pos = prior_start + np.nanargmin(prior_window)
                    if (
                        close_vals[i] < close_vals[prior_min_pos]
                        and not np.isnan(kst_vals[i])
                        and not np.isnan(kst_vals[prior_min_pos])
                        and kst_vals[i] > kst_vals[prior_min_pos]
                    ):
                        confirmed_until = i + valid_bars
        prev_min_idx = cur_min_idx
        if i <= confirmed_until:
            flag[i] = True

    return pd.Series(flag, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    signal_period: int = 9,
    trend_window: int = 200,
    divergence_lookback: int = 20,
    divergence_valid_bars: int = 10,
    extreme_exit: float = 100.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kst, signal = _kst(close, signal_period=signal_period)
    ema200 = close.ewm(span=trend_window, adjust=False).mean()
    trend_ok = close > ema200

    div_flag = _bullish_divergence_flag(
        close, kst, divergence_lookback, divergence_valid_bars
    )

    cross_up = (kst > signal) & (kst.shift(1) <= signal.shift(1))
    cross_down = (kst < signal) & (kst.shift(1) >= signal.shift(1))

    entry_signal = cross_up & div_flag & trend_ok
    exit_signal = cross_down | (kst > extreme_exit)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry_signal.values
    exit_vals = exit_signal.values
    for i in range(len(close)):
        if in_position:
            if bool(exit_vals[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
