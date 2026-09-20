"""Strategy: Sample Entropy (SampEn) regime filter gating an SMA trend
crossover entry.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per GospodarValovaHR's "Sample Entropy (SampEn) Regime Detector" TradingView
indicator (https://www.tradingview.com/script/1ZBMuq8g-Sample-Entropy-SampEn-Regime-Detector/,
read via browser_exec after web_search's DDGS backend TLS-erroring on the
detail-formula follow-up query): Sample Entropy quantifies how
predictable/regular vs. chaotic/random recent price action is over a
rolling window. LOW SampEn indicates a structured phase (strong trend or
clean mean-reversion) where standard trend/momentum strategies work well;
HIGH SampEn indicates pure randomness/"chop" where trades are more likely
to be fake-outs. The source's own suggested use: treat the regime like a
traffic light -- only take standard trend/momentum trades when SampEn is
low (predictable), and flag SampEn > ~2.0 as a high-noise regime to avoid
or de-risk.

This strategy operationalizes that regime filter on daily OHLCV: gate a
plain SMA(fast) > SMA(slow) trend-following long entry by requiring rolling
Sample Entropy of log returns to be BELOW sampen_threshold (i.e. only trade
the trend signal when the market is in the source's "structured/Green"
regime). First Sample-Entropy-based strategy in this repo (0 prior
"sample entropy"/"sampen" hits in strategies_index.jsonl) -- distinct from
Approximate Entropy (1 prior entry) since SampEn explicitly corrects for
ApEn's self-matching bias (different algorithm, not a parameter variant).

Signal logic
------------
- Sample Entropy (SampEn(m, r)): classic Richman & Moorman (2000) definition
  on a rolling window of `sampen_window` daily log returns, embedding
  dimension `m` (default 2), tolerance `r` = `r_mult` * rolling std of the
  window (default 0.2, the standard convention). SampEn = -ln(A/B) where B
  counts embedded-vector pairs within tolerance r at length m, and A counts
  the same pairs extended to length m+1 (both excluding self-matches).
  Higher SampEn = more irregular/chaotic; lower = more regular/predictable.
- Entry (long): SMA(fast) crosses above SMA(slow) (standard trend
  crossover) AND rolling SampEn < sampen_threshold (structured/predictable
  regime, source's own "Green" condition).
- Exit: SMA(fast) crosses back below SMA(slow), OR rolling SampEn rises to/
  above sampen_threshold (regime turning chaotic), OR max_hold_days elapses
  (safety backstop).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _sample_entropy(window: np.ndarray, m: int, r: float) -> float:
    """Richman & Moorman (2000) Sample Entropy for one window of values."""
    n = len(window)
    if n <= m + 1:
        return np.nan

    def _count_matches(mm: int) -> int:
        templates = np.array([window[i : i + mm] for i in range(n - mm + 1)])
        count = 0
        for i in range(len(templates)):
            dists = np.max(np.abs(templates[i + 1 :] - templates[i]), axis=1) if i + 1 < len(templates) else np.array([])
            count += int(np.sum(dists <= r))
        return count

    b = _count_matches(m)
    a = _count_matches(m + 1)
    if b == 0 or a == 0:
        return np.nan
    return -np.log(a / b)


def _rolling_sample_entropy(
    log_ret: pd.Series, window: int, m: int = 2, r_mult: float = 0.2
) -> pd.Series:
    vals = log_ret.values
    n = len(vals)
    out = np.full(n, np.nan)
    for end in range(window, n):
        w = vals[end - window : end]
        std = w.std()
        if std <= 0:
            out[end] = np.nan
            continue
        r = r_mult * std
        out[end] = _sample_entropy(w, m=m, r=r)
    return pd.Series(out, index=log_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    sampen_window: int = 60,
    sampen_m: int = 2,
    sampen_r_mult: float = 0.2,
    sampen_threshold: float = 1.8,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    sampen = _rolling_sample_entropy(log_ret, sampen_window, m=sampen_m, r_mult=sampen_r_mult)
    # forward-fill isolated NaN gaps (e.g. degenerate zero-std windows) so a
    # single bad window doesn't spuriously flip the regime gate
    sampen_ff = sampen.ffill()

    trend_up = sma_fast > sma_slow
    trend_up_prev = trend_up.shift(1)
    cross_up = trend_up & (~trend_up_prev.fillna(False))
    cross_down = (~trend_up) & trend_up_prev.fillna(False)

    regime_ok = sampen_ff < sampen_threshold

    entry = cross_up & regime_ok
    exit_signal = cross_down | (~regime_ok)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_arr = entry.fillna(False).values
    exit_arr = exit_signal.fillna(True).values
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_arr[i]):
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
