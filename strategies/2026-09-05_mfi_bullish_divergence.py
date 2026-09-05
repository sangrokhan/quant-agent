"""Strategy: Money Flow Index (MFI) bullish divergence, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-061):
Per FxOpen's "Money Flow Index Trading Strategies" article (MFI Divergence
section): a bullish divergence -- price makes a new N-bar low while MFI (the
volume-weighted RSI analog, bounded 0-100) makes a HIGHER low over the same
swing -- signals weakening selling pressure despite the new price low.
Traders go long when MFI subsequently crosses back above 20 (recovering out
of oversold), with a stop below the recent divergence low. This is a
distinct construction from every prior MFI/divergence strategy in this repo:
2026-09-04-033 used a plain MFI oversold-bounce (no divergence, no
price-vs-oscillator comparison); 2026-09-05-011 used %B+MFI dual-thrust
STRENGTH confirmation (buys overbought conditions, opposite economic logic);
2026-09-04-088 tested OBV divergence (different underlying oscillator: OBV
is a cumulative unbounded volume-direction sum, MFI is a bounded
volume-weighted RSI); 2026-09-05-057 tested RVI divergence (RVI measures
close-vs-open range position, unrelated to volume flow).

Signal logic
------------
- MFI(mfi_window) computed from typical price ((H+L+C)/3) and volume, per
  the standard money-flow-ratio -> 100-100/(1+ratio) formula.
- Bullish divergence check: close makes a new swing_lookback-bar low AND
  MFI's value on that bar is HIGHER than MFI's own swing_lookback-bar low
  from the prior occurrence (i.e. MFI did not confirm the new price low).
- Entry (long): a bullish divergence was flagged within divergence_recency
  bars AND MFI crosses back above the oversold_level (20 canonical).
- Exit: MFI crosses back below the oversold_level after topping out
  (momentum fading), OR a max_hold_days time-stop, OR close falls below the
  divergence-low stop level (source's own stop-loss rule).
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


def _mfi(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    raw_money_flow = typical_price * df["volume"]
    tp_diff = typical_price.diff()

    positive_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    negative_flow = raw_money_flow.where(tp_diff < 0, 0.0)

    pos_sum = positive_flow.rolling(window).sum()
    neg_sum = negative_flow.rolling(window).sum()

    money_ratio = pos_sum / neg_sum.replace(0.0, np.nan)
    mfi = 100 - (100 / (1 + money_ratio))
    mfi = mfi.fillna(50.0)
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_window: int = 14,
    swing_lookback: int = 10,
    oversold_level: float = 20.0,
    divergence_recency: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mfi = _mfi(df, mfi_window)

    price_rolling_low = close.rolling(swing_lookback).min()
    mfi_rolling_low = mfi.rolling(swing_lookback).min()

    price_is_new_low = close <= price_rolling_low
    # bullish divergence: current bar is a new price low, but MFI's own
    # rolling low over the SAME window is higher than MFI's value at the
    # prior occurrence of a price low (i.e. MFI's low over this window is
    # higher than it was swing_lookback bars ago at the previous low).
    mfi_low_prior = mfi_rolling_low.shift(swing_lookback)
    bullish_divergence = price_is_new_low & (mfi_rolling_low > mfi_low_prior)

    divergence_recent = bullish_divergence.rolling(divergence_recency, min_periods=1).max().astype(bool)

    mfi_cross_up = (mfi > oversold_level) & (mfi.shift(1) <= oversold_level)
    mfi_cross_down = (mfi < oversold_level) & (mfi.shift(1) >= oversold_level)

    entry = divergence_recent & mfi_cross_up

    divergence_low = close.where(bullish_divergence).ffill()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = np.nan

    close_vals = close.to_numpy()
    entry_vals = entry.to_numpy()
    exit_cross_vals = mfi_cross_down.to_numpy()
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
