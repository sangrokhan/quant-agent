"""Strategy: DeMarker(5) deep-oversold mean reversion on TLT (fixed income),
with a next-bar-high signal-based exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per QuantifiedStrategies.com's "5 Algorithmic Trading Strategies 2026"
(https://www.quantifiedstrategies.com/algorithmic-trading-strategies/),
Strategy #4 in the listicle: "We use a 5-day lookback period, and we enter
a position when the DeMarker indicator is below 10. We sell when the
close ends higher than yesterday's high." The source explicitly notes
"this strategy also works well with long-term Treasuries" -- this repo's
2 prior DeMarker entries (2026-09-04-154 accepted on QQQ using a
threshold-CROSS entry with a 200d trend filter + time-stop exit;
2026-09-10-126 a divergence variant) both used QQQ/SPY equity only and
neither used this source's specific mechanics: (1) a short 5-day DeMarker
lookback (vs the classic 14-day default used in both prior entries), (2)
DeM<10 as a simple LEVEL threshold rather than a cross, (3) NO trend
filter at all, and (4) the source's own signature signal-based exit
(close > yesterday's high) rather than a time-stop or overbought-cross
exit. This entry isolates that exact mechanism AND tests it on the exact
asset class (long-term Treasuries) the source itself calls out as also
working well -- TLT is the first Treasury-ETF DeMarker test in this repo.

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


def _demarker(df: pd.DataFrame, dem_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    de_max = (high - high.shift(1)).clip(lower=0.0)
    de_min = (low.shift(1) - low).clip(lower=0.0)
    sma_max = de_max.rolling(dem_window).mean()
    sma_min = de_min.rolling(dem_window).mean()
    denom = sma_max + sma_min
    dem = (sma_max / denom).where(denom > 0, 0.5)
    return dem


def generate_signals(
    price_df: pd.DataFrame,
    dem_window: int = 5,
    oversold_threshold: float = 0.10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: DeMarker(dem_window) < oversold_threshold (level trigger, no
    trend filter, matching the source's own disclosed rule exactly).
    Exit: close > prior day's high (source's own signature exit).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    dem = _demarker(df, dem_window)
    entry_trigger = (dem < oversold_threshold).shift(1).fillna(False)
    exit_trigger = (close > high.shift(1)).shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
    strategy_ret = position * daily_ret
    return strategy_ret
