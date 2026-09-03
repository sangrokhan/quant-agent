"""Strategy: QQQ Bollinger-Band mean reversion, gated by a volatility regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-001):
QQQ tends to mean-revert intraday-to-multiday after closing outside its
20-day Bollinger Bands, but ONLY during low/normal realized-volatility
regimes; during high-vol regimes (e.g. 2022 rate-hike drawdown, 2020 COVID
crash) breakouts tend to continue (trend) rather than revert, so an
unconditional mean-reversion rule should underperform. This is distinct from
the previously-rejected SMA-crossover trend strategy (2026-09-01-001, which
failed walk-forward specifically because of regime-dependence around the
2022 rate-hike period) — here we explicitly filter OUT the regime that broke
that strategy, rather than trading through it blindly.

Signal logic
------------
- 20-day realized volatility (std of daily log returns, annualized) is
  compared to its trailing 1-year (252d) median -> "low-vol regime" when
  current 20d vol <= 1.0x that median.
- Entry (long): close crosses below the lower 20-day Bollinger Band
  (2 std) AND we are in a low-vol regime.
- Exit: close crosses back above the 20-day SMA (mean reversion target),
  OR the volatility regime flips to high-vol (risk-off exit), OR after a
  max holding period of 10 trading days (avoid indefinite holds).
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- that's handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame) -> pd.Series
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


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    import math

    df = _prep(price_df)
    close = df["close"]

    daily_log_ret = pd.Series(index=close.index, dtype=float)
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)

    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    entry = (close < lower_band) & low_vol_regime.fillna(False)
    exit_meanrev = close > sma
    exit_regime_flip = ~low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
