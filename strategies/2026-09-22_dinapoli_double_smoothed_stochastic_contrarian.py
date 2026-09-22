"""Strategy: DiNapoli double-smoothed stochastic contrarian crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per the Backtrader Strategy Compendium's "Mean Reversion" digest
(https://backtrader.readthedocs.io/en/latest/strategies-series/en/02-mean-reversion.html,
Deep Dive 2 "KDJ and DiNapoli -- Taming a Twitchy Oscillator", read via
browser_exec this iteration), Joe DiNapoli's stochastic recipe takes an
8-period raw %K and applies TWO recursive exponential smoothings (a Wilder-
style running average, not a plain SMA/EMA):

    raw_k = 100 * (close - rolling_min(low, 8)) / (rolling_max(high, 8) - rolling_min(low, 8))
    sto[t] = sto[t-1] + (raw_k[t] - sto[t-1]) / slow_k      # slow_k=3
    sig[t] = sig[t-1] + (sto[t]  - sig[t-1]) / slow_d       # slow_d=3

The contrarian entry rule disclosed in the source: the main smoothed line
(sto) crossing BELOW the signal line (sig) is the BUY signal -- i.e. betting
that the oscillator's first downward step off a local high precedes a
price bounce (pure mean reversion, opposite of a standard stochastic
"golden cross" trend-following rule). Exit is the mirror condition: sto
crosses back ABOVE sig. The source ran this on a 6-hour XAUUSD frame and
got a low-frequency, low-drawdown result (24 trades / 3 months, 58% win
rate) -- the double smoothing turns an aggressive raw-stochastic whipsaw
into a rare, holdable signal. This is economically consistent with mean
reversion: two layers of recursive smoothing lag price enough that a
crossover under the signal line reflects an already-decelerating decline
(exhaustion), not a fresh breakdown.

This repo has zero prior DiNapoli-stochastic entries (searched
knowledge_base/strategies_index.jsonl for "DiNapoli.*[Ss]toch" -> 0
matches; 3 prior double-smoothed-stochastic entries -- Schaff Trend Cycle,
DSS Bressert, Premier Stochastic Oscillator -- all use different smoothing
constructions and none implement DiNapoli's specific recursive %K/%D
Wilder-style smoothing or its explicit contrarian crossunder-buy /
crossover-sell rule). We add a max_hold_days time-stop backstop (the
source's own low-frequency signal already discourages this, but without a
disclosed stop the position could otherwise run indefinitely in the
grid-test framework) and gate re-entry only when flat.

Signal logic
------------
- raw_k: 8-period (%k_period) raw stochastic %K from high/low/close.
- sto: recursive average of raw_k with period slow_k (default 3).
- sig: recursive average of sto with period slow_d (default 3).
- Entry (long): sto crosses from above sig to at/below sig (sto[t-1] > sig[t-1]
  and sto[t] <= sig[t]).
- Exit: sto crosses back above sig, OR max_hold_days holding-period time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dinapoli_stochastic(
    df: pd.DataFrame, k_period: int = 8, slow_k: int = 3, slow_d: int = 3
) -> tuple[pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    lowest = low.rolling(k_period).min()
    highest = high.rolling(k_period).max()
    raw_range = (highest - lowest).replace(0.0, pd.NA)
    raw_k = 100.0 * (close - lowest) / raw_range
    raw_k = raw_k.fillna(50.0)  # neutral value when range is flat/undefined

    values = raw_k.tolist()
    n = len(values)
    sto = [0.0] * n
    sig = [0.0] * n
    prev_sto = None
    prev_sig = None
    for i in range(n):
        v = values[i]
        if v != v:  # NaN (not yet enough data for raw_k)
            sto[i] = float("nan")
            sig[i] = float("nan")
            continue
        if prev_sto is None:
            prev_sto = v
        else:
            prev_sto = prev_sto + (v - prev_sto) / max(1, slow_k)
        if prev_sig is None:
            prev_sig = prev_sto
        else:
            prev_sig = prev_sig + (prev_sto - prev_sig) / max(1, slow_d)
        sto[i] = prev_sto
        sig[i] = prev_sig

    sto_s = pd.Series(sto, index=df.index)
    sig_s = pd.Series(sig, index=df.index)
    return sto_s, sig_s


def generate_signals(
    price_df: pd.DataFrame,
    k_period: int = 8,
    slow_k: int = 3,
    slow_d: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    sto, sig = _dinapoli_stochastic(df, k_period=k_period, slow_k=slow_k, slow_d=slow_d)

    sto_prev = sto.shift(1)
    sig_prev = sig.shift(1)

    entry = (sto_prev > sig_prev) & (sto <= sig)
    exit_signal = (sto_prev <= sig_prev) & (sto > sig)

    entry = entry.fillna(False)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
