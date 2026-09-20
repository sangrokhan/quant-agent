"""Strategy: Z-Score RSI mean reversion (long only), entry/exit on RSI-of-RSI
z-score extremes, with a fixed-bar time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-138):
Per Ali Casey's StatOasis article "The Better-RSI Showdown: We Tested 4 RSI
Upgrades on SPY, QQQ, IWM, and DIA"
(https://statoasis.com/overfit/research/better-rsi-backtest, visited via
browser_exec this iteration, 1,856-backtest study), the StatOasis "Z-Score
RSI" formulation -- first compute Wilder RSI(14), then re-express each RSI
reading as a rolling z-score over the past 20 RSI readings (population std)
-- beat the plain-RSI baseline on every measure tested: higher median CAR
(1.05% vs -0.15%), higher median CAR/MaxDD (0.030 vs 0.000), and lower
median max drawdown (38.27% vs 40.65%) across SPY/QQQ/IWM/DIA. The source's
single best reliable (>=50 trades) variant across all four RSI families was
specifically Z-Score RSI on QQQ Long: rsi_len=14, z_lookback=20, entry when
z <= -2.0, exit when z >= 1.0 OR after a 5-bar time exit, CAR/MaxDD 1.170,
WinPct 64.8%, 182 trades. This construction is distinct from every prior
plain-RSI-threshold or Connors-RSI strategy already tried in this repo
(id search: "z-score rsi"/"zscore rsi" -> zero prior matches; 19 prior
"Connors RSI" entries are a different composite indicator, not a z-scored
RSI reading) and is a first-time "RSI applied to itself via rolling z-score"
construction here, as opposed to z-scoring raw price/returns.

Signal logic
------------
- Wilder RSI(rsi_len) computed on close (via a standard Wilder smoothing
  RSI implementation, not vectorbt's own since we need the raw column for
  further transformation).
- z = (RSI - rolling_mean(RSI, z_lookback)) / rolling_std(RSI, z_lookback,
  population ddof=0), matching the source's stated methodology.
- Entry (long): z crosses at/below entry_z (extreme oversold-relative-to-
  RSI's-own-recent-range).
- Exit: z crosses at/above exit_z (mean-reversion target), OR
  max_hold_days bars have elapsed since entry (matching the source's 5-bar
  best-variant time exit; source's fills were signal-at-close / fill-at-
  next-open, approximated here as same-day close-to-close position with a
  1-day shift in generate_returns, consistent with every other strategy in
  this repo).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _wilder_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder's smoothing == EMA with alpha = 1/length
    avg_gain = gain.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)  # no losses -> RSI=100
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_len: int = 14,
    z_lookback: int = 20,
    entry_z: float = -2.0,
    exit_z: float = 1.0,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _wilder_rsi(close, rsi_len)
    roll_mean = rsi.rolling(z_lookback).mean()
    roll_std = rsi.rolling(z_lookback).std(ddof=0)
    z = (rsi - roll_mean) / roll_std.replace(0.0, float("nan"))

    entry = z <= entry_z
    exit_meanrev = z >= exit_z

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
