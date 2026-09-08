"""Strategy: Williams %R + Bollinger middle-band reversal with ATR stop/target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-004):
Per Tradie Capital's DEFI backtest snapshot
(https://www.tradiecapital.com/blog/backtests/defi-williams-bbands-reversal-strategy-backtest),
a long-only reversal signal combining Williams %R(14) recovering from
oversold with price still below the 20-day Bollinger middle band, exited on
mean-reversion to the middle band OR Williams %R turning overbought OR an
ATR-scaled stop/target, may capture short-term reversals more cleanly than
either indicator alone. Source reported (single ticker DEFI, 16 trades):
50% win rate, 1.36 profit factor, +2.71% return, 4.78% max drawdown -- this
iteration tests whether the same rule combination generalizes across
QQQ/SPY/BTC/ETH rather than one thinly-traded ticker.

Signal logic
------------
- WILLR(14): Williams %R over trailing 14 days, scaled -100..0.
- Entry (long): WILLR(14) crosses above -80 (recovering from oversold)
  AND close <= 20-day Bollinger middle band (SMA20) (still below the mean).
- Exit: close >= SMA20 (mean-reversion target) OR WILLR(14) > -20
  (overbought) OR ATR-scaled stop/target hit (stop_atr_mult * ATR(14) below
  entry price, target_atr_mult * ATR(14) above entry price) OR
  max_hold_days elapsed (avoid indefinite holds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _willr(df: pd.DataFrame, window: int) -> pd.Series:
    high_max = df["high"].rolling(window).max()
    low_min = df["low"].rolling(window).min()
    denom = (high_max - low_min).replace(0, float("nan"))
    willr = -100.0 * (high_max - df["close"]) / denom
    return willr


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    willr_window: int = 14,
    willr_entry_thresh: float = -80.0,
    willr_exit_thresh: float = -20.0,
    bb_window: int = 20,
    atr_window: int = 14,
    stop_atr_mult: float = 2.75,
    target_atr_mult: float = 3.99,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    willr = _willr(df, willr_window)
    willr_prev = willr.shift(1)
    willr_cross_up = (willr_prev <= willr_entry_thresh) & (willr > willr_entry_thresh)

    sma = close.rolling(bb_window).mean()
    atr = _atr(df, atr_window)

    entry_signal = willr_cross_up & (close <= sma)
    exit_meanrev = close >= sma
    exit_overbought = willr > willr_exit_thresh

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    close_vals = close.values
    atr_vals = atr.values
    entry_sig_vals = entry_signal.fillna(False).values
    exit_mr_vals = exit_meanrev.fillna(False).values
    exit_ob_vals = exit_overbought.fillna(False).values
    position_vals = position.values.copy()

    for i in range(len(close_vals)):
        if in_position:
            held = i - entry_idx
            price = close_vals[i]
            stop_hit = price <= stop_price
            target_hit = price >= target_price
            if (
                bool(exit_mr_vals[i])
                or bool(exit_ob_vals[i])
                or stop_hit
                or target_hit
                or held >= max_hold_days
            ):
                in_position = False
                position_vals[i] = 0
                continue
            position_vals[i] = 1
        else:
            if bool(entry_sig_vals[i]) and atr_vals[i] == atr_vals[i]:  # not NaN
                in_position = True
                entry_idx = i
                entry_price = close_vals[i]
                stop_price = entry_price - stop_atr_mult * atr_vals[i]
                target_price = entry_price + target_atr_mult * atr_vals[i]
                position_vals[i] = 1
            else:
                position_vals[i] = 0
    return pd.Series(position_vals, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
