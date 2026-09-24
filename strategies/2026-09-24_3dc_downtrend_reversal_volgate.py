"""Strategy: 3DC (3-day trend compression) pattern with a realized-vol
regime gate and a tighter fixed-fraction stop-loss, revisiting this cron
trigger's own recorded near-miss (2026-09-24-125) to fix its disclosed
excessive drawdown and parameter instability.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/3DC.html (Thomas Bulkowski's
write-up of Andrea Unger's "The Trend Compression Pattern," Technical
Analysis of Stocks & Commodities, February 2024; browser_exec fallback --
web_search's DDGS backend cannot usefully extract thepatternsite.com, as
with every prior entry from this domain this cron trigger).

This is a direct fix attempt for this same cron trigger's own recorded
near-miss (2026-09-24-125, base 3DC downtrend-reversal strategy): that
entry's own rejection reason was "both symbols fail max drawdown (0.287
SPY / 0.381 QQQ vs 0.25 threshold) and parameter sensitivity (relative
std 1.023 SPY / 1.540 QQQ vs 0.5 threshold)... A future iteration could
revisit this with an added volatility-regime gate or tighter stop-loss to
control drawdown" -- notes verbatim suggested exactly this fix, following
the same "revisit prior near-miss with the suggested fix" pattern already
used successfully in this repo (e.g. Adaptive SuperSmoother
2026-09-17-060/2026-09-18-037).

Two changes from the base 3DC strategy (same identification/entry rules
otherwise -- see 2026-09-24_3dc_downtrend_reversal.py for the full
source-hypothesis writeup):
    1. Realized-vol regime gate: flatten (skip new entries, and force-exit
       any open position) when trailing `vol_window`-day realized
       volatility exceeds `vol_regime_ratio` times its own trailing
       `vol_lookback`-day median -- the same vol-regime-gate pattern
       already used successfully in this repo's
       2026-09-03_bb_meanrev_qqq_volregime.py and the Adaptive
       SuperSmoother rescue (2026-09-17-060), directly targeting the
       near-miss's excessive-drawdown failure mode (large drawdowns
       cluster in high-vol regimes).
    2. Tighter fixed-fraction stop-loss: instead of the base strategy's
       "penny below the pattern bottom" stop (which can be arbitrarily
       far from entry on a wide 3-bar range), this variant additionally
       caps the stop distance to `max_stop_pct` of the entry price,
       whichever is TIGHTER (nearer to entry) -- directly bounding
       per-trade loss magnitude, targeting the same drawdown failure mode
       from the position-sizing side.

First 3DC-with-vol-gate variant in this repo. Distinct from the base 3DC
strategy (2026-09-24-125, rejected) via these two additions.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    compression_ratio: float = 0.5,
    target_mult: float = 1.5,
    max_hold_days: int = 20,
    max_stop_pct: float = 0.06,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series for 3DC pattern
    completions, traded only after a downtrend, gated off during
    high-realized-vol regimes, with a capped stop-loss distance."""
    df = _prep(price_df)
    h, l, c = df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()

    daily_log_ret = np.log(c / c.shift(1))
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    h_a = h.to_numpy()
    l_a = l.to_numpy()
    c_a = c.to_numpy()
    sma_a = sma.to_numpy()
    low_vol_a = low_vol_regime.to_numpy()

    entries: dict[int, tuple[float, float]] = {}

    for t in range(2, n):
        a, mid, b = t - 2, t - 1, t
        if np.isnan(sma_a[a]) or c_a[a] >= sma_a[a]:
            continue

        height1 = h_a[a] - l_a[a]
        height2 = h_a[mid] - l_a[mid]
        height3 = h_a[b] - l_a[b]
        total12 = height1 + height2
        if total12 <= 0:
            continue
        if not (height3 < compression_ratio * total12):
            continue

        pattern_high = max(h_a[a], h_a[mid], h_a[b])
        pattern_low = min(l_a[a], l_a[mid], l_a[b])
        height = pattern_high - pattern_low
        if height <= 0:
            continue
        target_price = pattern_high + height * target_mult

        for j in range(b + 1, n):
            if not low_vol_a[j]:
                # regime gate: don't take new entries while high-vol
                continue
            if c_a[j] > pattern_high:
                if j not in entries:
                    entry_price = c_a[j]
                    raw_stop = pattern_low
                    capped_stop = entry_price * (1.0 - max_stop_pct)
                    stop_price = max(raw_stop, capped_stop)  # tighter of the two
                    entries[j] = (target_price, stop_price)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = np.inf
    stop_price = -np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            # regime-flip force exit: high vol during the hold -> flatten
            if not low_vol_a[t]:
                in_pos = False
                position[t] = 0
                continue
            position[t] = 1
            held = t - entry_idx
            hit_target = c_a[t] >= target_price
            hit_stop = c_a[t] < stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=c.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
