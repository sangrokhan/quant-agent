"""Strategy: RSI(2) TREND-RESUMPTION confirmation entry (Alvarez) with a
FAST RSI-recovery exit (direct follow-up to 2026-09-17-002's near-miss).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-003),
sourced from the same article read this cron trigger, Cesar Alvarez's "Mean
Reversion Entry Timing":
https://alvarezquanttrading.com/blog/mean-reversion-entry-timing/

Direct follow-up to this same cron trigger's 2026-09-17-002 (RSI(2)
trend-resumption entry + N-day low-of-lows trailing exit), which was
rejected as a NEAR-MISS: full-sample Sharpe 0.871 (QQQ) / 0.643 (SPY)
against the 1.0 threshold, while MDD/transaction-cost-survival/parameter-
sensitivity all passed. That report's own notes flagged the slow N-day
low-of-lows exit as the likely main driver of the shortfall (not the
confirmation-gated entry timing itself), and recommended testing the same
novel trend-resumption entry mechanic against a FASTER exit instead.

The source article itself directly supports this: its own "Trend
Resumption - RSI Exit" comparison row (RSI(2) crossing back above an
exit threshold, not an N-day low) reported materially higher average CAR
than the "Entry on Open" baseline in the source's own test. This strategy
swaps this repo's slow low-of-lows exit for a fast RSI-recovery exit
(RSI(2) crosses back above rsi_exit), keeping the trend-resumption
confirmation entry unchanged.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    rsi_entry: float = 15.0,
    rsi_exit: float = 60.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Long-only {0,1} position series.

    Setup bar: close > SMA(trend_window) AND RSI(rsi_window) <= rsi_entry.
    Confirmation/entry bar: the first subsequent bar whose HIGH exceeds the
    setup bar's own high ("trend resumption" entry, per the source).
    Exit: RSI(rsi_window) closes above rsi_exit (fast mean-reversion
    recovery exit, source's own RSI-exit variant) OR a max_hold_days
    time-stop backstop.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    rsi = _rsi(close, rsi_window)
    trend_sma = close.rolling(trend_window).mean()
    above_trend = (close > trend_sma).fillna(False)
    setup = (above_trend & (rsi <= rsi_entry)).fillna(False)

    exit_rsi_trigger = (rsi > rsi_exit).fillna(False)

    n = len(close)
    setup_vals = setup.values
    high_vals = high.values
    exit_vals = exit_rsi_trigger.values

    pos_vals = [0] * n
    in_position = False
    pending_setup_high = None
    hold_count = 0

    for i in range(n):
        if in_position:
            hold_count += 1
            if exit_vals[i] or hold_count >= max_hold_days:
                in_position = False
                pos_vals[i] = 0
                hold_count = 0
            else:
                pos_vals[i] = 1
        else:
            if pending_setup_high is not None:
                if high_vals[i] > pending_setup_high:
                    in_position = True
                    pos_vals[i] = 1
                    hold_count = 0
                    pending_setup_high = None
                    continue
                if setup_vals[i]:
                    pending_setup_high = high_vals[i]
                pos_vals[i] = 0
            else:
                if setup_vals[i]:
                    pending_setup_high = high_vals[i]
                pos_vals[i] = 0

    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
