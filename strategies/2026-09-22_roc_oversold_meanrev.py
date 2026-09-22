"""Strategy: Price Rate of Change (ROC) oversold mean-reversion (oscillating).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-061):
Per QuantifiedStrategies.com's "Price Rate of Change Strategy (ROC Indicator
- Trading Rules and Backtest, Performance)"
(https://www.quantifiedstrategies.com/rate-of-change-trading-strategy/, read
via browser_exec this iteration -- web_extract's ddgs backend cannot fetch
page bodies), the article backtests 4 ROC variants on SPY: (1) "oversold -
oscillating" mean reversion, (2) breakouts, (3) zero-line crosses, and (4)
divergences (not backtested by the source, "difficult to quantify"). Of the
3 backtested, the source explicitly states variant (1) oversold-oscillating
had the best/most reasonable performance stats (669 trades, avg gain 0.4
after costs, best lookback settings 4-6 days), while breakout and zero-line
crossing variants "fall short" (poor profit factor). This repo already
tested plain zero-line-crossover ROC (2026-09-11-092, accepted on equity)
-- this iteration targets the DISTINCT oversold-oscillating mean-reversion
variant instead: short-lookback ROC dropping to an extreme negative
threshold (oversold), then reverting/oscillating back up through that
threshold, entered as a long within an uptrend filter (source's own
long-term-direction caveat: "cannot be used for long-term trading... use
with a trend filter").

Signal logic
------------
- Compute ROC(roc_window) = (close - close.shift(roc_window)) / close.shift(roc_window) * 100.
- Long entry: ROC crosses back above -oversold_level after having been
  below it (oscillating recovery from an oversold dip) AND close > SMA(trend_window)
  (source's own long-term-direction caveat -- avoid countertrend entries).
- Exit: ROC rises above exit_level (mean-reversion target reached, i.e. the
  bounce has run its course) OR close falls back below SMA(trend_window)
  (trend break) OR a max_hold_days time-stop.
- Flat otherwise. Long-only (no short per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _roc(close: pd.Series, roc_window: int) -> pd.Series:
    prior = close.shift(roc_window)
    return (close - prior) / prior * 100.0


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 5,
    oversold_level: float = 8.0,
    exit_level: float = 2.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    roc = _roc(close, roc_window)
    sma_trend = close.rolling(trend_window).mean()

    was_oversold = (roc < -oversold_level).rolling(roc_window, min_periods=1).max().astype(bool)
    recovering = roc > -oversold_level
    uptrend = close > sma_trend

    entry_trigger = (was_oversold.shift(1).fillna(False) & recovering & uptrend).fillna(False)
    exit_trigger_level = (roc > exit_level).fillna(False)
    exit_trigger_trend = (~uptrend).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    idx_list = df.index
    for i in range(len(idx_list)):
        if not in_position:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
        else:
            held = i - entry_idx
            if bool(exit_trigger_level.iloc[i]) or bool(exit_trigger_trend.iloc[i]) or held >= max_hold_days:
                in_position = False
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    roc_window: int = 5,
    oversold_level: float = 8.0,
    exit_level: float = 2.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        roc_window=roc_window,
        oversold_level=oversold_level,
        exit_level=exit_level,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
