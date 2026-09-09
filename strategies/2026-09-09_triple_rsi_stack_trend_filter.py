"""Strategy: Triple RSI (3/7/14) stacked crossover, gated by a long-term EMA
trend filter and an ATR-based stop-loss / time-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://goldscalpers.com/blog/triple-rsi-strategy ("Triple RSI Strategy
(3-7-14): Does It Really Win 90% of the Time?"), three RSI lines of
different lookbacks (fast=3, medium=7, slow=14) computed on the same series
and "stacked" (fast > medium > slow, all rising through a bullish crossover)
represent short-, medium-, and long-term momentum agreeing simultaneously --
a stronger entry filter than any single RSI threshold. The source explicitly
warns the raw crossover (no stop, no trend filter, no risk-reward rule)
produces a misleadingly high "win rate" with poor expectancy, and prescribes
three fixes: (1) a swing-based/ATR stop-loss, (2) a higher-timeframe trend
filter (e.g. 200-period EMA), (3) a fixed risk-reward exit. This strategy
operationalizes all three for this repo's daily-bar contract:

Signal logic
------------
- RSI(rsi_fast), RSI(rsi_mid), RSI(rsi_slow) computed via Wilder's smoothing.
- Long entry: RSI_fast crosses above RSI_mid AND RSI_mid > RSI_slow (stack
  confirmed) AND close > EMA(trend_window) (higher-timeframe trend filter).
- Exit: RSI_fast crosses back below RSI_mid (stack breaks), OR close drops
  atr_stop_mult * ATR(atr_window) below the entry-day close (stop-loss), OR
  a max_hold_days time-stop (approximates the source's fixed risk-reward
  exit within this repo's position-series contract, which has no explicit
  price target mechanism).
- Flat otherwise.

Distinct from prior RSI-family entries in this repo (single-RSI mean
reversion/momentum variants, dual-RSI agreement, RSI+BB/MACD confirmation,
Connors composite RSI) -- this is the first three-horizon-RSI *stack*
crossover combined with a long-term trend filter and ATR stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py): both generate_signals and
generate_returns accept the strategy's tunable parameters as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(100.0).where(avg_loss != 0, 100.0)
    rsi = rsi.mask(avg_gain == 0, 0.0)
    return rsi.astype(float)


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_fast: int = 3,
    rsi_mid: int = 7,
    rsi_slow: int = 14,
    trend_window: int = 200,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rf = _wilder_rsi(close, rsi_fast)
    rm = _wilder_rsi(close, rsi_mid)
    rs = _wilder_rsi(close, rsi_slow)

    ema_trend = close.ewm(span=trend_window, min_periods=trend_window, adjust=False).mean()
    atr = _atr(df, atr_window)

    stack_bull_now = (rm > rs)
    cross_up = (rf.shift(1) <= rm.shift(1)) & (rf > rm)
    cross_down = (rf.shift(1) >= rm.shift(1)) & (rf < rm)
    trend_ok = close > ema_trend

    entry = cross_up & stack_bull_now & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_close = 0.0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stack_break = bool(cross_down.iloc[i])
            stop_hit = bool(close.iloc[i] <= entry_close - atr_stop_mult * atr.iloc[entry_idx]) if pd.notna(atr.iloc[entry_idx]) else False
            if stack_break or stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_close = float(close.iloc[i])
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
