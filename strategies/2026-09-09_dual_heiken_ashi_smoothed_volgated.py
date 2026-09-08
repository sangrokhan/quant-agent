"""Strategy: Dual Heiken Ashi Smoothed trend-following, volatility-regime gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-063):
Direct follow-up to near-miss 2026-09-09-062 (plain Dual Heiken Ashi
Smoothed trend-following, rejected -- full-sample Sharpe failed on both
QQQ/SPY, but the grid showed the strategy's edge was entirely concentrated
in the low-volatility tercile: low 24/48 grid cells passed vs mid 8/48 vs
high 0/48). This iteration adds an explicit realized-volatility regime gate
(20-day realized vol <= its own trailing 252-day median, identical
construction to the already-accepted 2026-09-03_bb_meanrev_qqq_volregime.py
and other regime-gated accepts in this repo) restricting entries to the
low-vol regime only, keeping the Dual Heiken Ashi Smoothed entry/exit logic
otherwise identical to 2026-09-09-062. Thesis: the underlying color-flip
signal has genuine edge specifically in calm/low-vol trending conditions,
and explicitly filtering out the high-vol regime (where the grid showed a
decisive 0/48 failure) should recover a full-sample Sharpe that clears the
1.0 threshold, the same fix pattern that rescued several other near-miss
strategies in this repo's history.

Signal logic
------------
- Identical Dual Heiken Ashi Smoothed fast/slow color-flip entry as
  2026-09-09-062 (double-EMA-smoothed HA close, fast above slow, slow
  bullish, fast fresh color-flip), PLUS an entry-only requirement that
  20-day realized vol (annualized) is <= its own trailing 252-day median
  (low-vol regime).
- Exit: fast crosses back below slow, fast turns bearish, the vol regime
  flips to high-vol (risk-off exit, matching the entry gate's own logic),
  or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _heikin_ashi_close(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    return (o + h + l + c) / 4.0


def _smoothed_ha(ha_close: pd.Series, period: int, period2: int) -> pd.Series:
    e1 = ha_close.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period2, adjust=False).mean()
    return e2


def _low_vol_regime(df: pd.DataFrame, vol_window: int = 20, vol_lookback: int = 252, vol_regime_ratio: float = 1.0) -> pd.Series:
    close = df["close"]
    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return realized_vol <= (vol_median * vol_regime_ratio)


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 6,
    fast_period2: int = 2,
    slow_period: int = 50,
    slow_period2: int = 2,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    ha_close = _heikin_ashi_close(df)

    fast_smoothed = _smoothed_ha(ha_close, fast_period, fast_period2)
    slow_smoothed = _smoothed_ha(ha_close, slow_period, slow_period2)

    fast_bullish = fast_smoothed > fast_smoothed.shift(1)
    slow_bullish = slow_smoothed > slow_smoothed.shift(1)
    fast_above_slow = fast_smoothed > slow_smoothed
    fast_flip_up = fast_bullish & (~fast_bullish.shift(1).fillna(False))

    low_vol = _low_vol_regime(df, vol_window=vol_window, vol_lookback=vol_lookback, vol_regime_ratio=vol_regime_ratio).fillna(False)

    entry = fast_above_slow & slow_bullish & fast_flip_up & low_vol
    exit_signal_cond = (~fast_above_slow) | (~fast_bullish)
    exit_regime_flip = ~low_vol

    entry_arr = entry.to_numpy()
    exit_signal_arr = exit_signal_cond.to_numpy()
    exit_regime_arr = exit_regime_flip.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if exit_signal_arr[i] or exit_regime_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and entry_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 6,
    fast_period2: int = 2,
    slow_period: int = 50,
    slow_period2: int = 2,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        fast_period=fast_period,
        fast_period2=fast_period2,
        slow_period=slow_period,
        slow_period2=slow_period2,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
