"""Strategy: Range-band + IBS mean reversion with 300-day regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-133):
Per https://www.quantitativo.com/p/a-mean-reversion-strategy-with-211
("A Mean Reversion Strategy with 2.11 Sharpe"), the author's own
verified/re-tested rule set:
  1. Rolling mean of (High - Low) over `range_window` days (default 25).
  2. IBS = (Close - Low) / (High - Low).
  3. Lower band = rolling `band_window`-day High (default 10) minus
     `band_mult` (default 2.5) x the rolling mean range from step 1.
  4. Long entry when close closes BELOW the lower band AND IBS < `ibs_max`
     (default 0.3) -- an extended-and-oversold-close signal, distinct from
     plain IBS-only mean reversion (2026-09-04-089/158/159 in this repo,
     none of which use this specific rolling-High-minus-range-multiple band
     construction as a co-requirement).
  5. Exit when close > yesterday's high (source's own stated exit rule --
     a fast, single-bar-recovery exit, distinct from every other IBS
     variant's fixed-threshold or trend-filter exit already in this repo).
  6. Regime filter (source's own "Improvement 1", verified by the author to
     materially cut drawdown): only trade while close > SMA(`regime_window`)
     (source found 300 days works best on QQQ after testing 150/200/300);
     flat (100% cash) otherwise.

This is a genuinely distinct combination from every other IBS-family entry
in this repo (2026-09-04-089 IBS+200SMA-proximity-filter, 2026-09-04-158/159
N-day-averaged IBS, 2026-09-05-019 Adjusted-Failed-Bounce, 2026-09-07-005
IBS+5-day-low, 2026-09-08-001/016 IBS+gap combos) because of its specific
rolling-band construction (source's own "verification" of a blog claim) and
its next-bar-high recovery exit (not a fixed IBS threshold or a time-stop).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    range_window: int = 25,
    band_window: int = 10,
    band_mult: float = 2.5,
    ibs_max: float = 0.3,
    regime_window: int = 300,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    avg_range = (high - low).rolling(range_window).mean()
    lower_band = high.rolling(band_window).max() - band_mult * avg_range
    ibs = (close - low) / (high - low).replace(0, pd.NA)

    regime_sma = close.rolling(regime_window).mean()
    bull_regime = close > regime_sma

    entry_signal = (close < lower_band) & (ibs < ibs_max) & bull_regime.fillna(False)
    exit_signal = close > high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            # Also force-exit if regime flips bearish (source's own
            # regime-filter rule: "get to 100% cash in bear markets").
            if bool(exit_signal.iloc[i]) or not bool(bull_regime.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
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
