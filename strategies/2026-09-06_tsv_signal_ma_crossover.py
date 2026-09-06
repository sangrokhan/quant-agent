"""Strategy: Time Segmented Volume (TSV) zero-line + signal-MA crossover confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per QuantifiedStrategies.com's TSV article (Worden Brothers' Time Segmented
Volume indicator: price-change-weighted volume segmented over a rolling
window -- positive volume contribution when close > prior close, negative
when close < prior close, summed over the window), TSV rising above its own
zero baseline signals net accumulation/buying pressure, and the article's
own equity-curve chart caption explicitly shows "a 13-period moving average
smoothing line" applied to the raw TSV as "an objective signal filter."
QuantifiedStrategies' exact numeric backtest rule is paywalled, so this
repo also draws on a Google AI-overview synthesis of TradingView/
Investopedia TSV rules ("Moving Average Confirmation: enter when the TSV
histogram or line crosses above its signal moving average, especially if
the TSV value is transitioning from negative to positive territory")
combined with QuantifiedStrategies' 13-period TSV + MA-smoothing pairing to
build one concrete, testable rule: long entry on TSV crossing above its own
signal-line SMA while TSV is at/above zero (bullish momentum confirmed by
both the baseline AND the smoothing crossover, not either alone); exit on
the reverse crossover, TSV falling back below zero, or a time-stop.

First Time-Segmented-Volume-family strategy in this repo -- distinct from
every OBV/AD-Line/MFI/Chaikin-family volume indicator already tested,
because TSV weights VOLUME by the raw price CHANGE over the segment window,
not by dollar-flow (typical-price*volume) or a directional volume-only
sign.

Signal logic
------------
- TSV(tsv_window) = rolling sum over `tsv_window` bars of
  (close_t - close_{t-1}) * volume_t (a raw price-change * volume product,
  the classic TSV formula per the source's own description).
- signal = SMA(TSV, signal_window) (13-period smoothing per source's own
  chart caption, tunable).
- Entry (long): TSV crosses above signal AND TSV >= 0 (bullish momentum
  confirmed at/above the zero baseline).
- Exit: TSV crosses below signal, OR TSV falls below 0, OR a
  `max_hold_days` time-stop.
- Long-only, flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tsv(df: pd.DataFrame, tsv_window: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    price_change = close.diff()
    raw = price_change * volume
    return raw.rolling(tsv_window).sum()


def generate_signals(
    price_df: pd.DataFrame,
    tsv_window: int = 13,
    signal_window: int = 13,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    tsv = _tsv(df, tsv_window)
    signal = tsv.rolling(signal_window).mean()

    tsv_prev = tsv.shift(1)
    signal_prev = signal.shift(1)

    entry_trigger = (tsv > signal) & (tsv_prev <= signal_prev) & (tsv >= 0)
    exit_cross = (tsv < signal) & (tsv_prev >= signal_prev)
    exit_below_zero = tsv < 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            ec = bool(exit_cross.iloc[i]) if pd.notna(exit_cross.iloc[i]) else False
            ez = bool(exit_below_zero.iloc[i]) if pd.notna(exit_below_zero.iloc[i]) else False
            if ec or ez or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    tsv_window: int = 13,
    signal_window: int = 13,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, tsv_window=tsv_window, signal_window=signal_window, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
