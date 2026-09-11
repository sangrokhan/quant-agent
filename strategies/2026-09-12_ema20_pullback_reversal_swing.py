"""Strategy: 20-EMA pullback mean-reversion swing entry, per TradeZella
"Swing Trading Strategies That Actually Work in 2026" (Strategy 1: "Mean
Reversion to the 20 EMA"), https://www.tradezella.com/blog/swing-trading-strategies
(visited 2026-09-12, see knowledge_base/visited_pages.jsonl).

Source's disclosed rule (paraphrased to daily-bar OHLCV, no options/breadth
data needed -- feasible with data/loaders.py):
    Entry Criteria
    - Price above 200 EMA on daily (uptrend filter).
    - Price pulled back to within `pullback_pct` (source: 2%) of the 20 EMA.
    - RSI(14) between `rsi_low`/`rsi_high` (source: 40-55) -- a shallow,
      non-oversold pullback, not a capitulation dip.
    - Volume on the pullback bar below its 20-day average (quiet pullback,
      no distribution).
    - A bullish "reversal candle" at the 20 EMA (source: candle closes green
      / higher than it opened, i.e. close > open, as the simplest disclosed
      proxy for "reversal candle").
    Entry: close of the reversal candle (i.e. signal fires same bar).
    Stop / exit-if-wrong: close below the 20 EMA for `exit_confirm_days`
    (source: 2) consecutive days.
    Also apply a `max_hold_days` time-stop (not in source, added here as a
    standard guard against indefinite holds, consistent with prior
    strategies in this repo).

Novelty vs prior KB entries: distinct from the many EMA-crossover /
dual-EMA-trend strategies already tested (e.g. 2026-09-06-096 dual-EMA(20/50)
envelope breakout) -- this is a *pullback-to-EMA reversal-candle* mean
reversion construction with an explicit RSI band + low-volume-pullback
filter + 200-EMA regime gate, not a crossover or envelope-breakout rule.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 20,
    ema_trend: int = 200,
    pullback_pct: float = 0.02,
    rsi_window: int = 14,
    rsi_low: float = 40.0,
    rsi_high: float = 55.0,
    vol_window: int = 20,
    exit_confirm_days: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close.shift(1)
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    ema20 = close.ewm(span=ema_fast, adjust=False).mean()
    ema200 = close.ewm(span=ema_trend, adjust=False).mean()
    rsi = _rsi(close, rsi_window)
    avg_vol20 = volume.rolling(vol_window).mean()

    uptrend = close > ema200
    near_ema = (close - ema20).abs() <= (pullback_pct * ema20)
    rsi_band = (rsi >= rsi_low) & (rsi <= rsi_high)
    quiet_vol = volume < avg_vol20
    bullish_candle = close > open_

    entry = uptrend & near_ema & rsi_band & quiet_vol & bullish_candle
    entry = entry.fillna(False)

    below_ema = close < ema20
    exit_confirm = below_ema.rolling(exit_confirm_days).sum() >= exit_confirm_days

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_confirm.iloc[i]) or held >= max_hold_days:
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
