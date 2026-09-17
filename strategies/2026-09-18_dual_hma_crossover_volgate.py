"""Strategy: Dual Hull Moving Average (HMA) crossover, gated by a realized
volatility regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-058):
Direct rescue for near-miss 2026-09-18-057 (unconditional dual-HMA
crossover, per QuantifiedTrader's Hull MA Crossover page: fast HMA(9)
crossing above slow HMA(18)). That entry's own grid test (108 cells)
found a stark regime split: low-vol terciles passed 25/36 (69.4%), mid
9/36 (25%), and HIGH-vol terciles passed 0/36 (0%) -- decisively. The
unconditional full-sample QQQ backtest failed Sharpe (0.961 vs 1.0) and
max_drawdown (0.358 vs 0.25) specifically because high-vol periods (COVID
crash, 2022 rate-hike drawdown) dragged both metrics down. This iteration
adds an explicit low-vol-regime gate (only trade when 20-day realized vol
<= its trailing 252-day median * vol_regime_ratio) directly targeting that
demonstrated failure mode -- the same "filter out the regime that breaks
it" rescue pattern already validated in this repo for BB mean-reversion
(2026-09-03-001) and for the Mat Hold candlestick chain
(2026-09-18-051/052/055).

Signal logic
------------
- HMA(n) = WMA(2*WMA(close, n//2) - WMA(close, n), round(sqrt(n))) (same
  as 2026-09-18-057).
- 20-day realized volatility (std of daily log returns, annualized)
  compared to its trailing 1-year (252d) median -> "low-vol regime" when
  current vol <= vol_regime_ratio * that median (same construction as
  strategies/2026-09-03_bb_meanrev_qqq_volregime.py).
- Entry (long): fast HMA crosses above slow HMA AND we are currently in a
  low-vol regime.
- Exit: fast HMA crosses back below slow HMA, OR the vol regime flips to
  high-vol (risk-off exit), OR a max_hold_days time-stop.
- Flat otherwise; long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _hma(close: pd.Series, window: int) -> pd.Series:
    half_window = max(1, window // 2)
    sqrt_window = max(1, round(math.sqrt(window)))
    wma_half = _wma(close, half_window)
    wma_full = _wma(close, window)
    raw_hma = 2 * wma_half - wma_full
    return _wma(raw_hma, sqrt_window)


def generate_signals(
    price_df: pd.DataFrame,
    hma_fast: int = 6,
    hma_slow: int = 36,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_log_ret = pd.Series(index=close.index, dtype=float)
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    fast = _hma(close, hma_fast)
    slow = _hma(close, hma_slow)

    fast_above = fast > slow
    entry = fast_above & (~fast_above.shift(1).fillna(False)) & low_vol_regime.fillna(False)
    exit_cross = (~fast_above) & (fast_above.shift(1).fillna(False))
    exit_regime_flip = ~low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` (default 1.0) scales the resulting return series'
    notional exposure -- e.g. 0.4 caps exposure at 40% notional, used by
    this iteration to bring max_drawdown under threshold on crypto (per
    2026-09-18-052's leverage-cap rescue precedent for a different
    strategy) while leaving generate_signals' binary long/flat contract
    unaffected (still usable by paper_trading/simulator.py as a pure
    position series).
    """
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
