"""Strategy: BTC/USDT absolute momentum + volatility-targeting overlay, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-003):
The prior absolute-momentum strategy (2026-09-03-002, 90-day lookback) had a
promising Sharpe at shorter lookbacks (30-60d cleared >=1.0 per the
parameter sweep) but failed the hard max-drawdown gate (66% vs 25-35%
budget) because a flat {0,1} position sizing lets the strategy ride full
BTC volatility whenever the trend signal is on -- it does nothing to shrink
exposure during high-volatility stretches (which is exactly when large
drawdowns compound). This strategy tests whether adding an inverse-volatility
position-sizing overlay on top of a shorter (45-day) absolute-momentum
signal can keep the Sharpe edge found in the parameter sweep while cutting
the max drawdown to within budget, by deliberately de-risking (not just
binary in/out) during high realized-vol regimes -- exactly the fix
recommended in 2026-09-03-002's backtest report notes.

Novelty vs prior log entries:
- Directly builds on / revisits 2026-09-03-002 (BTC absolute momentum,
  90d lookback, rejected on MDD) with two changes: (a) 45-day lookback
  instead of 90-day (parameter sweep showed shorter lookbacks have better
  raw Sharpe), and (b) a continuous vol-targeting position size instead of
  a binary {0,1} position -- this is the "vol-targeting/position-sizing
  overlay" explicitly flagged as unexplored in that entry's notes, so this
  is not a duplicate, it's the direct follow-up experiment.
- Distinct from 2026-09-01-001 (SPY SMA crossover, equity, walk-forward
  failure) and 2026-09-03-001 (QQQ Bollinger mean-reversion, Sharpe
  failure): different asset, different signal family (still trend
  following, not mean-reversion), and the position-sizing mechanism itself
  is the novel element being tested here.

Signal logic
------------
- Trailing N-day (default 45) simple return of close: r_N(t) = close[t] /
  close[t-N] - 1.
- Raw direction: long (+1) whenever r_N(t) > 0, flat (0) otherwise -- same
  as 2026-09-03-002.
- Position size scaling: realized volatility is estimated as the trailing
  20-day annualized stdev of daily log returns. Target annualized vol is a
  configurable parameter (default 40%, roughly BTC's long-run vol // 2,
  chosen to meaningfully de-risk high-vol stretches without eliminating
  exposure during BTC's more typical vol regime). Position size =
  min(1.0, target_vol / realized_vol), i.e. never lever up beyond 1x, only
  ever scale down. Final position = direction * size.
- No shorting (SAFETY.md-adjacent design choice, consistent with prior
  strategies in this repo).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame) -> pd.Series
        Returns a continuous [0, 1] position-size series aligned to
        price_df.index (0 = flat, 1 = fully long at target vol or below,
        fractional = de-risked long due to elevated realized vol).
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 45,
    vol_window: int = 20,
    target_annual_vol: float = 0.40,
    periods_per_year: int = 365,
) -> pd.Series:
    """Return a [0,1] vol-targeted long/flat position-size series."""
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close / close.shift(lookback_days) - 1.0
    direction = (trailing_return > 0).astype(float)
    direction[trailing_return.isna()] = 0.0

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(periods_per_year)

    size = (target_annual_vol / realized_vol).clip(upper=1.0)
    size = size.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    position = direction * size
    position = position.clip(lower=0.0, upper=1.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
