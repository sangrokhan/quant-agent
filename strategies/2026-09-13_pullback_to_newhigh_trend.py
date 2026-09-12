"""Strategy: Buy-the-pullback, sell-the-new-high trend continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-017):
Per https://www.tradequantixnewsletter.com/p/momentum-mini-portfolio-development-302
(read via browser_exec this iteration), TradeQuantiX's "USA Pullback
Momentum" cross-sectional system only buys momentum stocks AFTER they've
had a pullback of X% off their highs (author settled on 15%, tested a
0-25% range), rather than the usual "buy at all-time highs" momentum entry.
The author's own isolated sub-study specifically buys the pullback and
sells at a new N-day high (tested N from 20 to 252 days, all qualitatively
similar) -- explicitly a trend-continuation exit (new high = trend resumed),
NOT a mean-reversion-to-moving-average exit like this repo's many prior
pullback strategies (DiNapoli displaced-MA, Keltner middle-line, Bollinger
middle-band, Woodie's CCI ZLR, TMF, CMO, etc. -- all of which exit when
price reverts back to some average/oscillator level). This single-symbol
adaptation swaps the source's cross-sectional stock-ranking universe for a
single-instrument trend-following filter (price above a long trend SMA)
combined with the same pullback-depth entry and new-high exit logic.

Signal logic
------------
- Trend filter: close > SMA(trend_window) (must be in an established
  uptrend, per the source's own "highest ranked" implying already-strong
  stocks -- we approximate cross-sectional strength with an absolute trend
  filter since we trade single symbols, not a stock universe).
- Entry (long): close is between (1 - pullback_pct) and (1 - pullback_pct/2)
  of the trailing high_lookback-day high (i.e. currently in a pullback of
  approximately pullback_pct off the highs -- not at a new high, not in a
  crash) AND the trend filter is satisfied.
- Exit: close makes a new exit_lookback-day high (trend resumed --
  source's own exit rule) OR a trailing stop of trailing_stop_pct off the
  post-entry peak is hit (source explicitly keeps a trailing stop) OR
  max_hold_days elapses (time-stop backstop consistent with this repo's
  other strategies).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py): both generate_signals and
generate_returns accept price_df plus the strategy's tunable parameters as
keyword arguments.
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
    high_lookback: int = 252,
    pullback_pct: float = 0.15,
    pullback_band: float = 0.5,  # width of the acceptance band, as a fraction of pullback_pct
    exit_lookback: int = 60,
    trend_window: int = 200,
    trailing_stop_pct: float = 0.15,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    in_uptrend = close > trend_sma

    rolling_high = close.rolling(high_lookback).max()
    pullback_frac = (rolling_high - close) / rolling_high

    lower_bound = pullback_pct * (1.0 - pullback_band)
    upper_bound = pullback_pct * (1.0 + pullback_band)
    in_pullback_zone = (pullback_frac >= lower_bound) & (pullback_frac <= upper_bound)

    entry = in_pullback_zone.fillna(False) & in_uptrend.fillna(False)

    exit_high = close.rolling(exit_lookback).max()
    # "new exit_lookback-day high" means today's close equals that rolling max
    # (shift(1) comparison avoids look-ahead: compare current close to the
    # highest close over the exit_lookback days ENDING today, which is
    # trivially true only on the day the new high is actually made because
    # the window includes today).
    made_new_high = close >= exit_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    peak_since_entry = None

    close_vals = close.values
    made_new_high_vals = made_new_high.values
    entry_vals = entry.values

    for i in range(len(close)):
        price_i = close_vals[i]
        if in_position:
            if peak_since_entry is None or price_i > peak_since_entry:
                peak_since_entry = price_i
            held = i - entry_idx
            trailing_stop_hit = (
                peak_since_entry is not None
                and price_i <= peak_since_entry * (1.0 - trailing_stop_pct)
            )
            if bool(made_new_high_vals[i]) or trailing_stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                peak_since_entry = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                peak_since_entry = price_i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    high_lookback: int = 252,
    pullback_pct: float = 0.15,
    pullback_band: float = 0.5,
    exit_lookback: int = 60,
    trend_window: int = 200,
    trailing_stop_pct: float = 0.15,
    max_hold_days: int = 60,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        high_lookback=high_lookback,
        pullback_pct=pullback_pct,
        pullback_band=pullback_band,
        exit_lookback=exit_lookback,
        trend_window=trend_window,
        trailing_stop_pct=trailing_stop_pct,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Position is applied to the NEXT day's return (avoid look-ahead: signal
    # computed using bar i's close, position held into bar i+1's return).
    strat_returns = daily_ret * position.shift(1).fillna(0)
    return strat_returns
