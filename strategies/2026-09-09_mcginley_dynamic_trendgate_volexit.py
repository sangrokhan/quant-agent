"""Strategy: Fast/Slow McGinley Dynamic crossover, gated by a 200-day SMA
uptrend filter and a realized-volatility regime exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-049):
Direct follow-up to this repo's near-miss 2026-09-04-127 (unconditional
McGinley Dynamic fast/slow crossover). That prior entry's grid showed
strong regime-conditional performance (best_cell Sharpe 1.946 in
low-vol) but decisively negative performance in the high-vol tercile
(0/24 grid cells passed), which dragged the full-sample Sharpe below
threshold on both QQQ (0.511) and SPY (0.721) even though MDD,
walk-forward, and parameter-sensitivity all passed cleanly.

This repo's own accumulated finding (e.g. 2026-09-03-021, 2026-09-04-089,
2026-09-07-007) is that adding a 200-day SMA uptrend gate improves most
crossover/pullback setups by filtering out counter-trend whipsaws -- the
exact failure mode implicated in -127's high-vol-regime collapse. This
iteration applies that same fix to the McGinley Dynamic crossover: only
take the fast-over-slow McGinley crossover entry when close is above its
own 200-day SMA (broad uptrend confirmation, per fxopen.com's own
"Higher-Timeframe Veto" filtering suggestion, visited this iteration),
plus an additional realized-volatility regime exit (flatten immediately
if 20-day realized vol exceeds its trailing-year median x vol_exit_ratio,
directly targeting -127's high-vol-regime failure rather than just hoping
the SMA filter alone fixes it).

Same McGinley Dynamic formula and crossover mechanics as -127
(fast_md crosses above slow_md = long entry; crosses below = exit), plus
the two new gates above. Everything else (asset universe, time-stop)
identical to -127 for a clean apples-to-apples comparison.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mcginley_dynamic(price: pd.Series, n: int) -> pd.Series:
    values = np.empty(len(price))
    values[:] = np.nan
    price_vals = price.values
    seeded = False
    md_prev = None
    for i in range(len(price_vals)):
        p = price_vals[i]
        if not seeded:
            if i + 1 >= n:
                md_prev = float(np.mean(price_vals[i + 1 - n : i + 1]))
                values[i] = md_prev
                seeded = True
            continue
        if md_prev is None or md_prev == 0 or p is None or np.isnan(p):
            values[i] = md_prev
            continue
        ratio = p / md_prev
        denom = n * (ratio ** 4)
        if denom == 0 or np.isnan(denom) or np.isinf(denom):
            md = md_prev
        else:
            md = md_prev + (p - md_prev) / denom
        values[i] = md
        md_prev = md
    return pd.Series(values, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_n: int = 10,
    slow_n: int = 30,
    max_hold_days: int = 20,
    trend_sma_window: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_exit_ratio: float = 1.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_md = _mcginley_dynamic(close, fast_n)
    slow_md = _mcginley_dynamic(close, slow_n)

    trend_sma = close.rolling(trend_sma_window).mean()
    uptrend = close > trend_sma

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    high_vol_regime = realized_vol > (vol_median_1y * vol_exit_ratio)

    cross_up = (fast_md > slow_md) & (fast_md.shift(1) <= slow_md.shift(1))
    cross_down = (fast_md < slow_md) & (fast_md.shift(1) >= slow_md.shift(1))

    entry_cond = cross_up & uptrend.fillna(False)
    exit_regime = high_vol_regime.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_cross = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            exit_vol = bool(exit_regime.iloc[i])
            if exit_cross or exit_vol or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
                in_pos = True
                hold_count = 0
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
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
