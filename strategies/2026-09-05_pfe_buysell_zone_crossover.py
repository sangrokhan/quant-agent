"""Strategy: Polarized Fractal Efficiency (PFE) buy/sell-zone threshold crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-014):
Polarized Fractal Efficiency (PFE, Hannula 1994, per Omega Research's
1997 EasyLanguage documentation) is a fractal-geometry measure of price
movement efficiency: the ratio of the straight-line (Euclidean) distance
between price N bars ago and today, versus the sum of bar-to-bar
Euclidean distances actually traveled over that window -- a value near
+/-100 means price moved in an almost straight, maximally efficient
line (strong trend); a value near 0 means price zig-zagged inefficiently
(chop/consolidation). The raw ratio is signed by the direction of the
N-bar price change (positive=uptrend-efficient, negative=downtrend-
efficient), then smoothed with a 3-period-equivalent EMA (alpha=1/3).
StockSpotter's own documented threshold convention treats a smoothed-PFE
cross above +50 ("BUYZONE") as a long entry signal and a cross below -50
("SELLZONE") as an exit/short signal.

First PFE strategy in this repo -- a fractal-efficiency-ratio
construction distinct from all prior oscillators (RSI-family compute
gain/loss ratios, OBV-family accumulate volume, TII/2026-09-04-123 sums
signed SMA-deviations rather than Euclidean path-length ratios).

Formula (exact, per MultiCharts/Omega Research's original EasyLanguage
PFE.ela source):
  straight_line_t = sqrt((close_t - close_{t-N})^2 + N^2)
  path_length_t = sum_{i=1..N} sqrt((close_{t-i+1} - close_{t-i})^2 + 1)
  frac_eff_t = round(straight_line_t / path_length_t * 100)
               * sign(close_t - close_{t-N})
  PFE_t = EMA(frac_eff, alpha=1/(smooth_period)), seeded with frac_eff_0

Signal logic
------------
- Entry (long): smoothed PFE crosses above buy_zone (+50 standard).
- Exit: smoothed PFE crosses below sell_zone (-50 standard, source's own
  SELLZONE), or a max_hold_days time-stop backstop (source gives no
  explicit stop rule beyond the two zone thresholds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _pfe(close: pd.Series, n: int, smooth_period: int) -> pd.Series:
    c = close.to_numpy()
    length = len(c)

    frac_eff = np.full(length, np.nan)
    for t in range(n, length):
        straight_line = np.sqrt((c[t] - c[t - n]) ** 2 + n ** 2)
        path_length = 0.0
        for i in range(1, n + 1):
            path_length += np.sqrt((c[t - i + 1] - c[t - i]) ** 2 + 1.0)
        ratio = (straight_line / path_length) * 100.0 if path_length != 0 else 0.0
        sign = 1.0 if (c[t] - c[t - n]) > 0 else (-1.0 if (c[t] - c[t - n]) < 0 else 0.0)
        frac_eff[t] = round(ratio) * sign

    frac_eff_s = pd.Series(frac_eff, index=close.index)

    alpha = 1.0 / smooth_period
    pfe = np.full(length, np.nan)
    first_valid = frac_eff_s.first_valid_index()
    if first_valid is None:
        return pd.Series(pfe, index=close.index)
    start_pos = close.index.get_loc(first_valid)
    pfe[start_pos] = frac_eff[start_pos]
    for t in range(start_pos + 1, length):
        prev = pfe[t - 1]
        cur = frac_eff[t]
        if np.isnan(cur):
            pfe[t] = prev
            continue
        pfe[t] = cur * alpha + prev * (1 - alpha)

    return pd.Series(pfe, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 9,
    smooth_period: int = 3,
    buy_zone: float = 50.0,
    sell_zone: float = -50.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pfe = _pfe(close, n, smooth_period)

    above_buy = pfe > buy_zone
    below_sell = pfe < sell_zone

    entry = above_buy & (~above_buy.shift(1).fillna(False))
    exit_signal = below_sell

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
