"""Strategy: Bollinger Band lower-touch + MACD bullish confirmation,
long-only, mean-reversion.

Hypothesis (see knowledge_base id 2026-09-06-154):
Per LuxAlgo's "Bollinger Bands and MACD: Entry Rules Explained"
(https://www.luxalgo.com/blog/bollinger-bands-and-macd-entry-rules-explained/):
"Long Entry Rules: Price touching or nearing the lower Bollinger Band, MACD
line crossing above the signal line, MACD histogram moving above zero,
Price starting to bounce upward from the lower band. Make sure all these
conditions line up before entering a trade." First plain (non-
Waddah-Attar-derived) MACD+Bollinger-Band combined-confirmation strategy in
this repo -- distinct from the already-rejected Waddah Attar Explosion
(2026-09-06-XXX, uses a proprietary combined trend_power metric rather than
independently confirming each indicator's own native signal).

Signal logic
------------
- Lower-band touch: close <= lower Bollinger Band (bb_window, bb_std) within
  the last touch_lookback bars (source says "touching or nearing" -- we
  require an actual touch/pierce within a short lookback window rather than
  requiring exact same-bar alignment, matching the source's looser "nearing"
  language).
- MACD bullish crossover: MACD line (ema_fast - ema_slow) crosses above its
  signal line (ema of MACD line, signal_window) on the current bar.
- MACD histogram above zero: histogram (MACD line - signal line) > 0 on the
  crossover bar (this is automatically implied by a crossover from below,
  but kept as an explicit gate per the source's own separate bullet).
- Price bounce confirmation: close > close.shift(1) (starting to bounce
  upward), per the source's 4th bullet.
- Entry: all four conditions true on the same bar -> long.
- Exit: close crosses back above the middle Bollinger Band (SMA, mean-
  reversion target) OR MACD line crosses back below its signal line
  (momentum reversal) OR a max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    touch_lookback: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    touched_lower = (close <= lower_band).rolling(touch_lookback, min_periods=1).max().astype(bool)

    ema_fast = close.ewm(span=macd_fast, adjust=False).mean()
    ema_slow = close.ewm(span=macd_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
    histogram = macd_line - signal_line

    bullish_cross = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    hist_above_zero = histogram > 0
    bouncing = close > close.shift(1)

    entry = touched_lower & bullish_cross & hist_above_zero & bouncing
    entry = entry.fillna(False)

    exit_meanrev = close > sma
    exit_momentum = macd_line < signal_line

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_momentum.iloc[i]) or held >= max_hold_days:
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
