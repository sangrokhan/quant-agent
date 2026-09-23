"""Strategy: SMA trend-following, gated to trade ONLY in the highest
realized-volatility regime (inverted vs. this repo's usual low-vol gates).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per Prashant Malan's SSRN paper "One Ticker Deep: The Trend Strategy That
Passed Every Test and Still Shouldn't Be Believed" (SSRN abstract_id=7073258,
read via browser_exec this iteration -- web_search DDGS/Yahoo backend
TLS-errored on every attempted query), a directional long-only time-series
trend rule ("hold the strongest names trading above their own moving
average, retreat to cash otherwise") passed walk-forward validation with
Sharpe 1.36-1.53, but the author's own attribution analysis showed the edge
is monotone in volatility and lives ENTIRELY in the highest-volatility
tercile of the universe -- in the lower two terciles the strategy
UNDERPERFORMS buy-and-hold. This is the mirror image of nearly every
vol-regime-gated strategy already tested in this repo (which gate trend/
mean-reversion signals to LOW-vol regimes, e.g. 2026-09-03_bb_meanrev; here
we explicitly test gating a plain SMA trend rule to the HIGH-vol tercile
only, motivated directly by this source's own disclosed finding).

Signal logic
------------
- 20-day realized volatility (std of daily log returns, annualized) ranked
  against its trailing 1-year (252d) rolling distribution -> a "high-vol
  regime" flag when current vol is at or above the `vol_percentile_floor`
  percentile of its own trailing history (default 0.667 = top tercile,
  matching the source's tercile split).
- Entry (long): close > SMA(trend_window) (source's own "trading above its
  own moving average" rule) AND we are in the high-vol regime.
- Exit: close crosses below SMA(trend_window), OR the vol regime drops out
  of the high tercile, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_percentile_floor: float = 0.667,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)

    # Rolling percentile rank of current vol within its own trailing history.
    def _pct_rank(window: pd.Series) -> float:
        if len(window) < 2:
            return float("nan")
        cur = window.iloc[-1]
        return (window <= cur).mean()

    vol_pct_rank = realized_vol.rolling(vol_lookback, min_periods=vol_window).apply(
        _pct_rank, raw=False
    )
    high_vol_regime = vol_pct_rank >= vol_percentile_floor

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = trend_up & high_vol_regime.fillna(False)
    exit_trend_break = ~trend_up
    exit_regime_flip = ~high_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
