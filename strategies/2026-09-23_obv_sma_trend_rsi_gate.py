"""Strategy: On-Balance-Volume (OBV) SMA-crossover, trend + RSI gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-129):
On-Balance Volume (Granville 1963) rising above its own short SMA, while
price is in a confirmed long-term uptrend (50-SMA > 200-SMA) and RSI is in
a neutral-to-bullish (not overbought) 40-70 band, signals genuine
accumulation pressure behind the move and should precede a further price
advance. Per NetPicks' "Mastering On Balance Volume (OBV)" strategy guide
(https://www.netpicks.com/mastering-on-balance-volume-obv/, read via
browser_exec this iteration -- web_search DDGS/Yahoo backend TLS-errored on
every query attempted this iteration).

Signal logic (long-only simplification of the source's long/short rules --
this repo's generate_signals contract is a single 0/1 long/flat series):
- OBV = cumulative sum of volume, added on up-close days, subtracted on
  down-close days (Granville's original formula).
- OBV SMA = obv_sma_window-period (default 10) simple moving average of OBV.
- Trend gate: SMA(trend_fast, default 50) > SMA(trend_slow, default 200).
- RSI(rsi_window, default 14) between rsi_low (40) and rsi_high (70).
- Entry (long): OBV crosses above its own SMA AND trend gate is true AND
  RSI is within [rsi_low, rsi_high].
- Exit: OBV crosses back below its own SMA, OR the trend gate flips false,
  OR a max_hold_days (default 20) time-stop is reached (source's ATR-based
  stop/target is approximated here via the time-stop + OBV-cross exit,
  since intraday ATR stop-loss execution isn't representable in this
  repo's daily-bar signal/position framework -- noted in notes field).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    obv_sma_window: int = 10,
    trend_fast: int = 50,
    trend_slow: int = 200,
    rsi_window: int = 14,
    rsi_low: float = 40.0,
    rsi_high: float = 70.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    direction = close.diff().apply(lambda d: 1 if d > 0 else (-1 if d < 0 else 0))
    obv = (direction * volume).fillna(0).cumsum()
    obv_sma = obv.rolling(obv_sma_window).mean()

    sma_fast = close.rolling(trend_fast).mean()
    sma_slow = close.rolling(trend_slow).mean()
    trend_gate = sma_fast > sma_slow

    rsi = _rsi(close, rsi_window)
    rsi_ok = (rsi >= rsi_low) & (rsi <= rsi_high)

    obv_above = obv > obv_sma
    obv_cross_up = obv_above & (~obv_above.shift(1).fillna(False))

    entry = obv_cross_up & trend_gate.fillna(False) & rsi_ok.fillna(False)
    exit_obv_cross_down = ~obv_above.fillna(False)
    exit_trend_flip = ~trend_gate.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_obv_cross_down.iloc[i]) or bool(exit_trend_flip.iloc[i]) or held >= max_hold_days:
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
