"""Strategy: RSI(4) oversold entry / RSI(55) exit, gated by a 200-day SMA
uptrend filter -- Larry Connors' public short-RSI mean-reversion rule set.

Hypothesis (see knowledge_base/strategies_log.jsonl id, this iteration):
Per a widely-cited r/algotrading summary of Larry Connors' original public
RSI mean-reversion rule (distinct from both this repo's already-accepted
RSI(2)/SMA(5)-recovery-exit variant, id=2026-09-03-005, and the already-
rejected RSI(10) 55/45 momentum-continuation variant, id=2026-09-04-077):
buy when price is above its 200-day SMA (long-term uptrend intact) AND a
short-lookback RSI(4) closes below an oversold threshold (30) -- indicating
a sharp short-term pullback within an otherwise healthy uptrend; exit
purely on RSI recovering above a fixed higher threshold (55), NOT on a
moving-average-recovery signal. The key structural difference from
2026-09-03-005 is the EXIT rule: a pure-RSI-level exit (55) rather than
close crossing back above SMA(5), which changes typical holding period and
trade-selection compared to the already-tested variant.

Signal logic
------------
- Trend filter: close > SMA(trend_window) (default 200).
- Entry (long): close > SMA(trend_window) AND RSI(rsi_window) crosses below
  entry_threshold (default 30) -- i.e. RSI was >= entry_threshold on the
  prior bar and is < entry_threshold today (a genuine cross, not a
  continuous gate, to avoid re-triggering every day RSI stays low).
- Exit: RSI crosses above exit_threshold (default 55), OR trend filter
  breaks (close falls below SMA(trend_window)), OR a max_hold_days
  time-stop (default 20 trading days) is reached, whichever comes first.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- that's handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index
        (1 = long, 0 = flat). Used directly by check_walk_forward /
        check_parameter_sensitivity via generate_returns, and exposed
        separately for paper_trading/simulator.py.
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
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 4,
    entry_threshold: float = 30.0,
    exit_threshold: float = 55.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rsi = _rsi(close, rsi_window)
    rsi_prev = rsi.shift(1)

    entry_cross = (rsi_prev >= entry_threshold) & (rsi < entry_threshold)
    entry = entry_cross & uptrend.fillna(False)

    exit_cross = (rsi_prev <= exit_threshold) & (rsi > exit_threshold)
    trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(trend_break.iloc[i]) or held >= max_hold_days:
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
