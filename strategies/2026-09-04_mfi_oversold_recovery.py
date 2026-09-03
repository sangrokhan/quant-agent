"""Strategy: Money Flow Index (MFI) oversold-recovery mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-033):
MFI (a volume-weighted RSI analog, 0-100 scale) dropping to/below an
oversold threshold (20) and then crossing back above it signals a
short-term mean-reversion buying opportunity, gated by a long-term uptrend
filter (close > 200d SMA) since the source (quantifiedstrategies.com)
explicitly notes buying oversold recoveries performs better on assets with
an upward drift (large-cap stocks/indices) than shorting overbought
extremes (which can stay elevated for weeks in a secular bull market).

The source's own concrete rule additionally requires a bullish/bearish
engulfing candlestick confirmation and a "range-bound, not strong-trend"
market classification -- neither is cleanly derivable from this repo's
daily OHLCV-only loaders without adding a discretionary pattern/regime
classifier, so this implementation uses the closest testable core
mechanism: MFI(14) oversold-threshold recovery cross, long-only, with the
200d SMA trend filter as the uptrend-drift proxy the source's own reasoning
relies on.

Signal logic
------------
- MFI(mfi_window) computed from typical price ((H+L+C)/3) x volume, with
  the standard positive/negative money flow ratio -> 100 - 100/(1+ratio).
- Entry (long): MFI crosses from <= oversold_threshold to > oversold_threshold
  (a fresh recovery cross, not every bar MFI stays low) AND close > SMA(trend_window).
- Exit: MFI >= overbought_threshold, OR after max_hold_days, whichever first.
- Flat otherwise; long-only, no shorting (consistent with this repo's
  convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

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

    positive_sum = positive_flow.rolling(window).sum()
    negative_sum = negative_flow.rolling(window).sum()

    # Avoid divide-by-zero: where negative_sum is 0, money ratio -> inf -> MFI -> 100.
    money_ratio = positive_sum / negative_sum.replace(0.0, pd.NA)
    mfi = 100 - (100 / (1 + money_ratio))
    mfi = mfi.fillna(100.0)
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_window: int = 14,
    oversold_threshold: float = 20.0,
    overbought_threshold: float = 80.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mfi = _mfi(df, mfi_window)
    trend_ok = close > close.rolling(trend_window).mean()

    recovery_cross = (mfi > oversold_threshold) & (mfi.shift(1) <= oversold_threshold)
    entry = recovery_cross & trend_ok.fillna(False)
    exit_overbought = mfi >= overbought_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or held >= max_hold_days:
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
