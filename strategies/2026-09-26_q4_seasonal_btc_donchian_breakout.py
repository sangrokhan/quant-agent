"""Strategy: Seasonal-Gated Q4 BTC Donchian Breakout (VoiceOfChain rules-based setup).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-012):
Per VoiceOfChain's "Crypto Seasonality Strategy: Rules Traders Can Use"
(https://voiceofchain.com/academy/crypto-seasonality-strategy, disclosed
free rule): Q4 (Oct-Dec) is historically the strongest risk-on seasonal
window for BTC in bull regimes. The source's own disclosed rules-based
seasonal breakout setup:
  - Bias: only trade long during the seasonal window, AND BTC above its
    50-day MA.
  - Entry: daily close above the rolling 20-day high (source describes a
    "retest" after the breakout, but the core trigger disclosed is the
    20-day-high breakout itself -- the retest/pullback confirmation is
    described narratively, not as a precise numeric rule, so this
    implementation uses the disclosed breakout trigger directly).
  - Stop: below the breakout candle's low, OR 1.5x daily ATR (whichever
    the source's own rule states: "breakout candle low or 1.5x daily ATR").
  - Exit (trail): trail the position below the 10-day EMA (source's own
    disclosed trailing mechanic for the remainder after a partial take
    profit -- simplified here to a single full-position trailing exit
    below the 10-day EMA, since this repo's generate_signals/generate_returns
    contract doesn't support partial position scaling).

This is the first calendar-gated (specific Oct-Dec seasonal window)
Donchian-breakout strategy in this repo -- distinct from the many
unconditional Donchian/Turtle breakout variants (2026-09-04-054,
2026-09-07-014, 2026-09-16-174/177) which trade breakouts year-round with
no seasonal bias filter.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    seasonal_months: tuple = (10, 11, 12),
    trend_ma_window: int = 50,
    entry_window: int = 20,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    trail_ema_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    trend_sma = close.rolling(trend_ma_window).mean()
    trend_ok = close > trend_sma

    in_season = pd.Series(df.index.month, index=df.index).isin(list(seasonal_months))

    donchian_upper = high.rolling(entry_window).max().shift(1)
    entry = (close > donchian_upper) & trend_ok & in_season

    atr = _atr(high, low, close, atr_window)
    trail_ema = close.ewm(span=trail_ema_window, adjust=False).mean()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    stop_level = None
    for i in range(len(close)):
        if in_position:
            # Trail exit: close below the 10-day EMA, or hard stop hit.
            hard_stop_hit = stop_level is not None and low.iloc[i] < stop_level
            trail_exit = close.iloc[i] < trail_ema.iloc[i]
            if hard_stop_hit or trail_exit:
                in_position = False
                stop_level = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                breakout_low = low.iloc[i]
                atr_stop = close.iloc[i] - atr_stop_mult * atr.iloc[i] if pd.notna(atr.iloc[i]) else breakout_low
                stop_level = min(breakout_low, atr_stop)
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
