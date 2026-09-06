"""Strategy: TRIX bullish divergence (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-018):
Per https://theindicatorlab.com/reviews/trix-triple-exponential-average/,
source's own disclosed divergence-trading rule: "Look for price making a
lower low while TRIX makes a higher low (bullish divergence). This is where
TRIX shines... The triple smoothing makes divergence signals more reliable
than with MACD." Default TRIX length 14 (own example on ES futures 1h with
a bullish divergence riding a 30-point move).

Distinct from this repo's existing TRIX strategy
(2026-09-04_trix_signalline_crossover.py, id 2026-09-04-038: signal-line
cross while TRIX>0, no divergence) -- this strategy trades the divergence
pattern itself as the entry trigger, not a crossover.

TRIX formula (standard):
    EMA1 = EMA(close, length)
    EMA2 = EMA(EMA1, length)
    EMA3 = EMA(EMA2, length)
    TRIX = 100 * (EMA3 / EMA3.shift(1) - 1)

Signal logic
------------
- Bullish divergence detection (same construction as
  2026-09-07_kst_bullish_divergence_trend_gated.py's divergence helper,
  applied to TRIX instead of KST): over a rolling `divergence_lookback`
  window, if price registers a new N-bar low while TRIX is ABOVE the TRIX
  value it had at the PRIOR N-bar low, that's a bullish divergence,
  confirmed for `divergence_valid_bars` bars.
- Entry (long): TRIX crosses above zero WHILE a bullish divergence flag is
  active (source's own emphasis: divergence trading, not plain zero-cross;
  gating the entry on TRIX turning positive avoids buying into a still-falling
  TRIX purely on the divergence pattern alone).
- Exit: TRIX crosses back below zero, or a `max_hold_days` time-stop
  (source doesn't specify an exit for the divergence trade itself, only for
  the separate zero-cross trend-confirmation strategy; this repo consistently
  adds a time-stop safety net).

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


def _trix(close: pd.Series, length: int = 14) -> pd.Series:
    ema1 = close.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    ema3 = ema2.ewm(span=length, adjust=False).mean()
    trix = 100.0 * (ema3 / ema3.shift(1) - 1.0)
    return trix.fillna(0.0)


def _bullish_divergence_flag(
    close: pd.Series, osc: pd.Series, lookback: int, valid_bars: int
) -> pd.Series:
    """True on bars where a bullish divergence was recently confirmed
    (price N-bar low with osc higher than at the prior N-bar low), and
    remains True for `valid_bars` bars after confirmation."""
    n = len(close)
    close_vals = close.values
    osc_vals = osc.values
    flag = np.zeros(n, dtype=bool)

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
        if cur_min_idx == i and cur_min_idx != prev_min_idx:
            prior_start = max(0, i - 2 * lookback)
            prior_end = max(0, i - lookback)
            if prior_end > prior_start:
                prior_window = close_vals[prior_start:prior_end]
                if len(prior_window) > 0 and not np.all(np.isnan(prior_window)):
                    prior_min_pos = prior_start + np.nanargmin(prior_window)
                    if (
                        close_vals[i] < close_vals[prior_min_pos]
                        and not np.isnan(osc_vals[i])
                        and not np.isnan(osc_vals[prior_min_pos])
                        and osc_vals[i] > osc_vals[prior_min_pos]
                    ):
                        confirmed_until = i + valid_bars
        prev_min_idx = cur_min_idx
        if i <= confirmed_until:
            flag[i] = True

    return pd.Series(flag, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 14,
    divergence_lookback: int = 20,
    divergence_valid_bars: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    trix = _trix(close, length=length)

    div_flag = _bullish_divergence_flag(
        close, trix, divergence_lookback, divergence_valid_bars
    )

    cross_up = (trix > 0) & (trix.shift(1) <= 0)
    cross_down = (trix < 0) & (trix.shift(1) >= 0)

    entry_signal = cross_up & div_flag
    exit_signal = cross_down

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    entry_vals = entry_signal.values
    exit_vals = exit_signal.values

    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_pos = True
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
