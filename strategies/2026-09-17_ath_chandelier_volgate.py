"""Strategy: All-time-high breakout + ATR chandelier stop, gated by a
low/mid volatility regime filter.

Hypothesis (direct follow-up to near-miss 2026-09-04-025, see
knowledge_base/strategies_log.jsonl): the original All-Time-High + ATR(10)
chandelier trailing-stop strategy (per QuantPedia/Wilcox & Crittenden,
"Does Trend Following Work on Stocks?") missed the Sharpe 1.0 threshold on
QQQ by only 3.4% (0.966 vs 1.0) despite passing every other validator
(MDD, TC-survival, walk-forward 4/4, very low parameter sensitivity). Its
own grid breakdown showed the edge was concentrated almost entirely in the
low-vol tercile (12/24 passing cells) with only 2/24 in mid-vol and 0/24 in
high-vol -- i.e. the strategy's few high-vol-regime trades were dragging
down the otherwise-strong low/mid-vol Sharpe. This strategy tests the
log's own suggested remedy: suppress new entries while the market is in a
HIGH realized-volatility regime (current 20-day realized vol > its trailing
252-day median by more than vol_regime_ratio), since the source signal
already has clean risk/reward exactly outside of that regime slice.
Distinct from the prior entry (2026-09-04-025, unconditional AT-time-high
entry, no regime gate) -- same core entry/exit mechanics otherwise.

Signal logic
------------
- ATR(atr_window) via the standard Wilder true-range average.
- All-time high tracked causally as the expanding max of daily closes up to
  (but not including) the current bar.
- 20-day realized volatility (std of daily log returns, annualized)
  compared to its trailing 252-day median -> "high-vol regime" when
  current vol > vol_regime_ratio x that median.
- Entry (long): today's close >= the all-time-high-so-far AND we are NOT
  currently in a high-vol regime.
- Chandelier trailing stop: once in a position, track the running highest
  close since entry; stop level = running_high - atr_multiplier *
  ATR(atr_window). Exit when close drops below the stop level (the vol
  regime is NOT re-checked mid-trade -- only gates new entries, matching
  this repo's established pattern of regime-gating entries only, e.g.
  2026-09-03-001).
- Flat otherwise; long-only, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def _high_vol_regime(
    close: pd.Series,
    vol_window: int,
    vol_lookback: int,
    vol_regime_ratio: float,
) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(252)
    trailing_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    # Causal: use yesterday's regime reading to gate today's entry.
    high_vol = (realized_vol > (vol_regime_ratio * trailing_median)).shift(1).fillna(False)
    return high_vol


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    atr_multiplier: float = 3.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, atr_window)

    all_time_high_prior = close.shift(1).expanding(min_periods=atr_window).max()
    high_vol = _high_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)
    entry = (close >= all_time_high_prior) & (~high_vol)
    entry = entry.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    running_high = None

    for i in range(len(close)):
        px = close.iloc[i]
        a = atr.iloc[i]
        if in_position:
            running_high = px if running_high is None else max(running_high, px)
            stop_level = running_high - atr_multiplier * (a if a == a else 0.0)
            if a == a and px < stop_level:
                in_position = False
                position.iloc[i] = 0
                running_high = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) and a == a:
                in_position = True
                running_high = px
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
