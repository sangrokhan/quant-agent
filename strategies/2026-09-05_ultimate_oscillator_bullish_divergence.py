"""Strategy: Ultimate Oscillator (UO) bullish divergence, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-077):
Per TradingView's Ultimate Oscillator (UO) reference and ArrowAlgo's UO algo
trading guide (Larry Williams, 1976; blends buying-pressure/true-range
ratios over 7/14/28-period windows weighted 4:2:1 into a bounded 0-100
oscillator): "Bullish Divergence forms meaning price forms a lower low
while UO makes a higher low. The low of the Divergence should be below 30.
UO breaks above the high of the Divergence [to trigger entry]." This is a
distinct construction from every prior divergence strategy in this repo:
2026-09-04-050 tested a plain UO oversold-threshold cross (no divergence,
no price-vs-oscillator comparison); 2026-09-05-061 (MFI) and 2026-09-04-088
(OBV) and 2026-09-05-057 (RVI) tested divergence on different underlying
oscillators (volume-weighted RSI analog, cumulative volume-direction sum,
and open/close-range position respectively) -- UO is the first
triple-timeframe buying-pressure/true-range blended oscillator tested for
divergence in this repo, and its source's own confirmation trigger ("UO
breaks above the high of the Divergence") differs mechanically from the
MFI variant's "cross back above oversold_level" trigger.

Signal logic
------------
- UO(short_w, mid_w, long_w) = 100 * (4*Avg7 + 2*Avg14 + Avg28) / 7, where
  Avg_n = sum(BuyingPressure, n) / sum(TrueRange, n), BuyingPressure =
  close - min(low, prior_close), TrueRange = max(high, prior_close) -
  min(low, prior_close). Standard Larry Williams weights 4:2:1 for
  short:mid:long window Avg terms.
- Bullish divergence check: close makes a new swing_lookback-bar low AND
  UO's own swing_lookback-bar low is HIGHER than UO's rolling low from the
  prior occurrence (UO did not confirm the new price low) AND that UO low
  was below oversold_level (30, source's own precondition).
- Entry (long): a bullish divergence was flagged within divergence_recency
  bars AND close/UO subsequently breaks above the UO value recorded at the
  divergence bar's rolling-window high (source's own confirmation trigger:
  "UO breaks above the high of the Divergence").
- Exit: UO crosses back below oversold_level, or a max_hold_days time-stop,
  or close falls below the divergence-low stop level.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _ultimate_oscillator(df: pd.DataFrame, short_w: int, mid_w: int, long_w: int) -> pd.Series:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    prior_close = close.shift(1)

    bp = close - pd.concat([low, prior_close], axis=1).min(axis=1)
    tr = pd.concat([high, prior_close], axis=1).max(axis=1) - pd.concat([low, prior_close], axis=1).min(axis=1)

    avg_short = bp.rolling(short_w).sum() / tr.rolling(short_w).sum().replace(0.0, np.nan)
    avg_mid = bp.rolling(mid_w).sum() / tr.rolling(mid_w).sum().replace(0.0, np.nan)
    avg_long = bp.rolling(long_w).sum() / tr.rolling(long_w).sum().replace(0.0, np.nan)

    uo = 100.0 * (4.0 * avg_short + 2.0 * avg_mid + avg_long) / 7.0
    return uo.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    short_w: int = 7,
    mid_w: int = 14,
    long_w: int = 28,
    swing_lookback: int = 10,
    oversold_level: float = 30.0,
    divergence_recency: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    uo = _ultimate_oscillator(df, short_w, mid_w, long_w)

    price_rolling_low = close.rolling(swing_lookback).min()
    uo_rolling_low = uo.rolling(swing_lookback).min()

    price_is_new_low = close <= price_rolling_low
    uo_low_prior = uo_rolling_low.shift(swing_lookback)
    bullish_divergence = (
        price_is_new_low
        & (uo_rolling_low > uo_low_prior)
        & (uo_rolling_low < oversold_level)
    )

    divergence_recent = bullish_divergence.rolling(divergence_recency, min_periods=1).max().astype(bool)

    # "UO breaks above the high of the Divergence": track the UO value at
    # the most recent divergence bar's rolling window and require UO to
    # subsequently exceed the max UO seen since the divergence bar.
    divergence_uo_at_flag = uo.where(bullish_divergence).ffill()
    uo_since_divergence_high = uo.where(bullish_divergence).ffill()
    # confirmation trigger: current UO exceeds the UO level recorded when
    # divergence flagged (approximation of "breaks above the high of the
    # divergence" using UO's own value at the flag as the reference high).
    confirm_break = uo > divergence_uo_at_flag.shift(1)

    entry = divergence_recent & confirm_break

    uo_cross_down = (uo < oversold_level) & (uo.shift(1) >= oversold_level)

    divergence_low = close.where(bullish_divergence).ffill()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = np.nan

    close_vals = close.to_numpy()
    entry_vals = entry.to_numpy()
    exit_cross_vals = uo_cross_down.to_numpy()
    div_low_vals = divergence_low.to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(stop_level)) and close_vals[i] < stop_level
            if bool(exit_cross_vals[i]) or held >= max_hold_days or stop_hit:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                stop_level = div_low_vals[i]
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
