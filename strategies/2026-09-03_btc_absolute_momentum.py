"""Strategy: BTC/USDT absolute (time-series) momentum, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-002):
BTC/USDT exhibits positive absolute (time-series) momentum: when the
trailing N-day total return is positive, the near-term forward return is on
average also positive (trend continuation), and when trailing return is
negative, staying flat avoids further downside. Economic rationale: crypto
markets are dominated by retail/momentum-chasing flows and slower
information diffusion than equities, so trends (once established) tend to
persist over multi-week horizons rather than mean-revert immediately.

Novelty vs prior log entries:
- Distinct from 2026-09-01-001 (SPY dual-SMA *crossover*, which failed
  walk-forward due to 2022 regime dependence): different asset class
  (crypto vs equity), and a different signal construction -- a single
  trailing-return threshold (absolute momentum / time-series momentum,
  Antonacci-style) rather than a two-moving-average crossover. It shares
  the general "trend-following" family, so this run explicitly evaluates
  walk-forward robustness (not just full-sample Sharpe) to catch the same
  regime-dependence failure mode if it's present here too.
- Distinct from 2026-09-02-001 (BTC funding-rate mean reversion, rejected
  at feasibility because funding-rate data isn't available): this strategy
  only needs OHLCV, which load_crypto already provides -- no new data
  plumbing required.
- Distinct from 2026-09-03-001 (QQQ Bollinger mean-reversion, rejected on
  Sharpe): this is a trend-following (not mean-reversion) idea, on crypto
  rather than equities.

Signal logic
------------
- Trailing N-day (default 90) simple return of close: r_N(t) = close[t] /
  close[t-N] - 1.
- Long (position=1) whenever r_N(t) > 0 (computed using data up to and
  including day t, no look-ahead: exposure realized the *next* day via the
  usual position.shift(1) convention in generate_returns).
- Flat (position=0) otherwise.
- No shorting (SAFETY.md-adjacent design choice, not a hard requirement --
  just keeps this a simple, easy-to-reason-about first cut).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index
        (1 = long, 0 = flat).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 90,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on trailing return sign."""
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close / close.shift(lookback_days) - 1.0
    position = (trailing_return > 0).astype(int)
    position[trailing_return.isna()] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
