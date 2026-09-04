"""Strategy: Percent B + Money Flow Index dual-thrust momentum confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-011):
John Bollinger's "Percent B and Money Flow" system (from his book
"Bollinger on Bollinger Bands", per StockCharts ChartSchool's full
disclosure) combines %B (price's location within its Bollinger Bands,
0=lower band, 1=upper band) with the Money Flow Index (MFI, a
volume-weighted RSI analog on typical price) to identify the START of a
new trend, not a mean-reversion setup: a surge in %B (strong upside price
thrust) confirmed by a high MFI reading (strong buying volume) together
signal the trend is just getting started, worth a long entry. Exact
source rule: buy when %B moves above 0.80 AND MFI moves above 80; sell/
exit when %B moves below 0.20 AND MFI moves below 20.

This is a MOMENTUM/thrust-confirmation combination -- explicitly distinct
from both prior standalone uses of these two indicators already tested
in this repo: Larry Connors' %B mean-reversion strategy (id=2026-09-04-107,
buys when %B < 0 i.e. price BELOW the lower band, opposite direction/
philosophy) and the standalone MFI oversold-bounce strategy
(id=2026-09-04-033, buys when MFI recovers from an oversold <20-25
reading, also opposite direction). This strategy buys STRENGTH (both
indicators simultaneously near their extreme HIGH) rather than buying
weakness/oversold dips.

Formula
-------
- Typical price TP = (high + low + close) / 3
- MFI: RSI-style oscillator (0-100) applied to raw money flow
  (TP * volume, signed by TP's direction vs prior TP), over mfi_window.
- %B = (close - lower_band) / (upper_band - lower_band), where
  upper/lower bands = SMA(bb_window) +/- bb_std * rolling_std(bb_window).

Signal logic
------------
- Entry (long): %B crosses above pct_b_high (0.80) AND MFI is
  simultaneously above mfi_high (80) at that bar (source's own exact
  numeric rule).
- Exit: %B crosses below pct_b_low (0.20) AND MFI is simultaneously
  below mfi_low (20), OR a max_hold_days time-stop backstop (source
  suggests Parabolic SAR for stops -- not implemented here; using a
  simple time-stop as this repo's standard backstop convention instead).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _percent_b(close: pd.Series, bb_window: int, bb_std: float) -> pd.Series:
    mid = close.rolling(bb_window, min_periods=max(2, bb_window // 2)).mean()
    std = close.rolling(bb_window, min_periods=max(2, bb_window // 2)).std()
    upper = mid + bb_std * std
    lower = mid - bb_std * std
    band_range = (upper - lower).replace(0.0, pd.NA)
    pct_b = (close - lower) / band_range
    return pct_b


def _mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, mfi_window: int) -> pd.Series:
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    tp_diff = typical_price.diff()
    pos_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    neg_flow = raw_money_flow.where(tp_diff < 0, 0.0)
    pos_sum = pos_flow.rolling(mfi_window, min_periods=max(2, mfi_window // 2)).sum()
    neg_sum = neg_flow.rolling(mfi_window, min_periods=max(2, mfi_window // 2)).sum()
    money_ratio = pos_sum / neg_sum.replace(0.0, 1e-9)
    mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    mfi_window: int = 14,
    pct_b_high: float = 0.80,
    pct_b_low: float = 0.20,
    mfi_high: float = 80.0,
    mfi_low: float = 20.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    pct_b = _percent_b(close, bb_window, bb_std)
    mfi = _mfi(high, low, close, volume, mfi_window)

    buy_thrust = (pct_b > pct_b_high) & (mfi > mfi_high)
    sell_thrust = (pct_b < pct_b_low) & (mfi < mfi_low)

    entry = buy_thrust & (~buy_thrust.shift(1).fillna(False))
    exit_signal = sell_thrust

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
