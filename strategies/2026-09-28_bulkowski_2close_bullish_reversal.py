"""Strategy: Bulkowski Bullish 2-Close Reversal (3-bar pattern), height-target exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-046),
sourced from https://thepatternsite.com/2Closebull.html (Thomas Bulkowski,
read via browser_exec -- web_extract ddgs backend is search-only and
cannot extract URL content).

Source's own identification rules (quoted/paraphrased):
  - 3-bar pattern.
  - Bar 1: any price bar.
  - Bar 2: makes a lower low than bar 1, AND closes below bar 1's close.
  - Bar 3: posts a lower low than bar 2's low, BUT closes above BOTH bar 1
    and bar 2's closes (the defining "2-close" reversal condition).
  - Breaks out upward 71% of the time (per source's own stats).

Source's own tested trading rules (used here, adapted to this repo's
daily-bar/long-only/no-intraday-stop convention):
  - Entry: a buy-stop a penny above the pattern's highest bar (bar1's
    high, since bars 2/3 make lower lows) -- approximated here as a
    next-bar entry once the pattern completes and the breakout condition
    (close > pattern high) is confirmed, since this repo's daily-bar
    backtest framework doesn't model intrabar stop orders.
  - Loss exit: a stop-loss a penny below the pattern's lowest bar (bar
    3's low, the pattern's lowest point) -- approximated as an exit on
    close falling below the pattern low.
  - Target exit: 2x the pattern height (highest bar minus lowest bar)
    added to the pattern's highest bar price -- exact height-target rule
    from the source, used here as a limit-style exit once close reaches
    that level.
  - A max_hold_days safety time-stop is added (source's own average hold
    times were 14-28 days across winners/losers, but did not specify an
    explicit maximum) to bound worst-case holding period, consistent with
    this repo's other Bulkowski-pattern strategies.

Source's OWN documented conclusion is an explicit negative prior ("This
pattern is a poor performer... Look elsewhere for a more promising
pattern... flops in both ETFs and cryptocurrency") -- this repo tests the
concrete numeric rule anyway (as with the Bollinger Band squeeze test
2026-09-03-011 and Fibonacci retracement test 2026-09-03-022, both of
which also started from a documented negative source prior) as an
independent falsification/confirmation check on this repo's own
QQQ/SPY/BTC/ETH universe.

Signal logic (daily bars, causal/no look-ahead):
1. Trend filter: close > SMA(trend_window) (default 200d) -- source's own
   stock test showed the pattern only marginally beats benchmark in an
   established UPTREND (not downtrend), so this repo's implementation
   restricts to the uptrend-inbound-trend case per the source's own
   stronger-performing scenario.
2. Pattern detection over a rolling 3-bar window ending at bar t-1
   (bars t-3, t-2, t-1 = bar1, bar2, bar3): bar2.low < bar1.low AND
   bar2.close < bar1.close AND bar3.low < bar2.low AND bar3.close >
   bar1.close AND bar3.close > bar2.close.
3. Entry (long): pattern confirmed at bar t-1 AND close at bar t breaks
   above the pattern's highest price (bar1's high) AND uptrend filter
   holds.
4. Exit: close falls below the pattern's lowest price (bar3's low, the
   stop-loss level) OR close reaches 2x pattern height above the pattern
   high (target exit) OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    trend_window: int = 200,
    target_height_mult: float = 2.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    n = len(close)
    close_v = close.values
    high_v = high.values
    low_v = low.values

    # For each bar t (the potential breakout bar), check if bars
    # [t-3, t-2, t-1] form the 2-close reversal pattern.
    pattern_high = pd.Series(float("nan"), index=close.index)
    pattern_low = pd.Series(float("nan"), index=close.index)
    pattern_confirmed = pd.Series(False, index=close.index)

    for t in range(3, n):
        i1, i2, i3 = t - 3, t - 2, t - 1
        bar1_low, bar1_close, bar1_high = low_v[i1], close_v[i1], high_v[i1]
        bar2_low, bar2_close = low_v[i2], close_v[i2]
        bar3_low, bar3_close = low_v[i3], close_v[i3]

        if (
            bar2_low < bar1_low
            and bar2_close < bar1_close
            and bar3_low < bar2_low
            and bar3_close > bar1_close
            and bar3_close > bar2_close
        ):
            pattern_confirmed.iloc[t] = True
            pattern_high.iloc[t] = bar1_high
            pattern_low.iloc[t] = bar3_low

    breakout = pattern_confirmed & (close > pattern_high)
    entry = breakout.fillna(False) & uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_loss_level = float("nan")
    target_level = float("nan")

    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_stop = close_v[i] < stop_loss_level
            hit_target = close_v[i] >= target_level
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                p_high = pattern_high.iloc[i]
                p_low = pattern_low.iloc[i]
                stop_loss_level = p_low
                target_level = p_high + target_height_mult * (p_high - p_low)
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
