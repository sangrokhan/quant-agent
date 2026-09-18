"""Strategy: Adaptive ATR-Percentile Grid Trading (QuantifiedStrategies.com).

Hypothesis (see knowledge_base/strategies_log.jsonl for this id): the
"Adaptive Grid Trading Strategy" activates a mean-reversion grid only
during HIGH relative-volatility regimes (ATR Percentile >= activation
threshold, e.g. 70-80th percentile of its own trailing 100-200-bar
history) and deactivates during low-vol regimes (<= 25-30th percentile),
using ATR-scaled grid spacing so the same percentile thresholds work
consistently across assets with very different absolute volatility (e.g.
BTC ~2% ATR vs SOL ~8% ATR, both at their own 85th percentile).

Source: https://www.quantifiedstrategies.com/adaptive-grid-trading-strategy/
(fully disclosed formula/thresholds; fetched via browser_exec -- web_search
DDGS backend failing this cron trigger).

Adaptation to this repo's long/flat position-series interface
----------------------------------------------------------------
A literal multi-order grid (placing several buy/sell limit orders around a
reference price) isn't expressible as a simple {0,1} position series. This
strategy operationalizes the SAME core "activate mean-reversion only in a
high-ATR-percentile regime" idea as a single-position long/flat rule:
- ATR Percentile = rolling rank of current ATR(14) within its own trailing
  `pctile_lookback` (default 200) bar history, expressed 0-100.
- Grid is "active" (mean-reversion trades allowed) only when ATR Percentile
  >= `activate_pctile` (default 75); deactivated (flat, no new entries, exit
  any open position) when ATR Percentile <= `deactivate_pctile` (default 25).
- While active: long entry when close drops `grid_spacing_atr_mult` x
  ATR(14) below its own rolling `grid_ref_window`-bar mean (a grid "buy
  level" touch); exit when close recovers back to (or above) that rolling
  mean (grid "sell level"), or a max_hold_days time-stop, or the regime
  deactivates (unwind, per source's own "exit and unwind" rule).

First ATR-Percentile-gated grid/mean-reversion strategy in this repo --
distinct from prior fixed-percentage-band or absolute-ATR-multiple
mean-reversion strategies (this one's defining feature is relative-history
percentile normalization, explicitly designed to need no per-asset
retuning).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr_percentile(atr: pd.Series, lookback: int) -> pd.Series:
    """Rolling rank of the current ATR within its own trailing window, 0-100."""
    def _pctile(window):
        current = window.iloc[-1]
        return (window <= current).sum() / len(window) * 100.0

    return atr.rolling(lookback, min_periods=lookback // 2).apply(_pctile, raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    atr_length: int = 14,
    pctile_lookback: int = 200,
    activate_pctile: float = 75.0,
    deactivate_pctile: float = 25.0,
    grid_ref_window: int = 20,
    grid_spacing_atr_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tr = _true_range(df)
    atr = tr.rolling(atr_length).mean()
    atr_pctile = _atr_percentile(atr, pctile_lookback)

    ref_mean = close.rolling(grid_ref_window).mean()
    buy_level = ref_mean - grid_spacing_atr_mult * atr

    active = atr_pctile >= activate_pctile
    deactivated = atr_pctile <= deactivate_pctile

    n = len(df)
    close_arr = close.to_numpy()
    buy_level_arr = buy_level.to_numpy()
    ref_mean_arr = ref_mean.to_numpy()
    active_arr = active.to_numpy()
    deactivated_arr = deactivated.to_numpy()

    position = [0.0] * n
    in_pos = False
    hold_count = 0

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                deactivated_arr[i]
                or (not pd.isna(close_arr[i]) and not pd.isna(ref_mean_arr[i]) and close_arr[i] >= ref_mean_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                position[i] = 1.0
        else:
            can_enter = (
                bool(active_arr[i])
                and not pd.isna(buy_level_arr[i])
                and not pd.isna(close_arr[i])
                and close_arr[i] <= buy_level_arr[i]
            )
            if can_enter:
                in_pos = True
                hold_count = 0
                position[i] = 1.0

    return pd.Series(position, index=df.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    atr_length: int = 14,
    pctile_lookback: int = 200,
    activate_pctile: float = 75.0,
    deactivate_pctile: float = 25.0,
    grid_ref_window: int = 20,
    grid_spacing_atr_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs -- applied separately)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        atr_length=atr_length,
        pctile_lookback=pctile_lookback,
        activate_pctile=activate_pctile,
        deactivate_pctile=deactivate_pctile,
        grid_ref_window=grid_ref_window,
        grid_spacing_atr_mult=grid_spacing_atr_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
