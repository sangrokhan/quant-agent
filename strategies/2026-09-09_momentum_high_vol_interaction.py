"""Strategy: Time-series adaptation of "Momentum and Reversal Combined with
Volatility Effect in Stocks" (Wei, "Do Momentum and Reversals Coexist?"),
summarized at
https://quantpedia.com/strategies/momentum-and-reversal-combined-with-volatility-effect-in-stocks
(knowledge_base id=2026-09-09-111).

Source's own cross-sectional construction (large-cap universe, 1964-2009):
sort stocks each month into quintiles by trailing 6-month return AND trailing
6-month realized volatility; go long the highest-return/highest-volatility
quintile, short the lowest-return/highest-volatility quintile. Reported
16.46% p.a. long-short, Sharpe 0.65. Fundamental reason (source's own): higher
information uncertainty (proxied by higher realized volatility) makes
investor under-reaction -- and therefore momentum continuation -- stronger,
not weaker; the effect concentrates in the high-vol quintile.

This is a single-asset time-series long-only adaptation (no cross-sectional
universe available here): go long only when BOTH (a) trailing formation-
window return is positive (momentum) AND (b) the asset's OWN realized
volatility is currently elevated relative to its own trailing history (percentile
rank of rolling vol >= vol_percentile_threshold) -- i.e. trade momentum only
during the asset's own high-information-uncertainty regime, flat otherwise.
This is distinct from the previously-rejected 2026-09-03-003 (BTC absolute
momentum + inverse-vol POSITION SIZING overlay, which de-risks in high vol);
here high vol is the entry GATE for momentum, not a sizing dampener -- the
source's finding is that momentum returns are actually stronger, not weaker,
in high-vol regimes.

Signal logic
------------
- formation_window-day trailing return (momentum signal).
- vol_window-day realized volatility (annualized stdev of daily log returns).
- vol_percentile_threshold: today's realized vol must rank at or above this
  percentile within its own trailing vol_lookback-day history (elevated-vol
  regime gate).
- Entry (long): trailing return > 0 AND vol percentile >= vol_percentile_threshold.
- Exit: momentum turns negative, vol regime falls back below threshold, or a
  max_hold_days time-stop (source rebalances every month with a 6-month hold;
  approximate with a hold-period time-stop here since this is a daily-signal
  time-series adaptation, not a monthly-rebalanced cross-sectional portfolio).
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
    formation_window: int = 126,
    vol_window: int = 126,
    vol_lookback: int = 252,
    vol_percentile_threshold: float = 0.5,
    max_hold_days: int = 126,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)

    trailing_return = close.pct_change(formation_window)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_percentile = realized_vol.rolling(vol_lookback, min_periods=vol_window).rank(pct=True)

    momentum_positive = trailing_return > 0
    high_vol_regime = vol_percentile >= vol_percentile_threshold

    entry = momentum_positive.fillna(False) & high_vol_regime.fillna(False)
    exit_signal = (~momentum_positive.fillna(False)) | (~high_vol_regime.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
