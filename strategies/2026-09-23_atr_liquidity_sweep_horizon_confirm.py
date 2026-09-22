"""Strategy: ATR-thresholded liquidity sweep with fixed-horizon reversal
confirmation (long side only).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per QuantParadox's two research articles on liquidity-sweep backtesting
(https://www.quantparadox.com/blog/liquidity-sweep-trading and
https://www.quantparadox.com/blog/backtest-liquidity-sweeps, both read this
iteration via browser_exec), a liquidity sweep must be defined mechanically
as FOUR separate, pre-committed decisions to avoid the tautology of
identifying a sweep only after it already reversed: (1) which levels
qualify -- a fixed-rule N-bar swing low/high, using only data available at
each bar (no look-ahead); (2) how far beyond counts as a poke -- expressed
in ATR units so the threshold is portable across volatility regimes,
rather than a fixed price/percent amount; (3) what counts as returning --
a CLOSE back inside the level (stricter than a same-bar wick-back-above,
which is what this repo's already-rejected SFP construction, id
2026-09-09-087, used); (4) a fixed confirmation horizon (confirm_bars)
after which an unreversed poke is treated as expired, not silently
included/excluded. This construction is distinct from 2026-09-09-087/089
(which required the wick-poke and close-back-above to happen on the SAME
bar, and used a plain N-bar low with no ATR-denominated threshold) by
allowing the reversal confirmation up to confirm_bars later and by
ATR-scaling the poke depth.

Signal logic
------------
- swing_low = rolling N-bar low of `low`, computed on data STRICTLY prior
  to the current bar (shift(1)) to avoid look-ahead.
- poke_depth = ATR(atr_window); a bar "pokes" the level when
  low < swing_low - poke_atr_mult * poke_depth.
- After a poke at bar i, look forward up to confirm_bars bars (inclusive)
  for the first bar whose CLOSE > swing_low (confirmed reversal). Enter
  long at that confirmation bar's close (captured via next-bar return per
  the standard shift(1) exposure convention below).
- If no confirmation occurs within confirm_bars, the poke expires (no
  trade).
- Exit: max_hold_days time-stop after entry, OR close falls back below
  swing_low (invalidation).
- Optional close>SMA(trend_window) uptrend gate (trend_filter=True by
  default, matching most other mean-reversion/reversal entries in this
  repo).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


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
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 10,
    poke_atr_mult: float = 0.5,
    confirm_bars: int = 3,
    max_hold_days: int = 8,
    atr_window: int = 14,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(close)

    swing_low = low.rolling(swing_window).min().shift(1)
    atr = _atr(df, atr_window)
    poke = (low < (swing_low - poke_atr_mult * atr)).fillna(False)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = bool(close.iloc[i] < swing_low.iloc[i]) if pd.notna(swing_low.iloc[i]) else False
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        if bool(poke.iloc[i]) and pd.notna(swing_low.iloc[i]) and bool(uptrend.iloc[i]):
            level = swing_low.iloc[i]
            confirmed_at = None
            for j in range(i, min(i + confirm_bars + 1, n)):
                if close.iloc[j] > level:
                    confirmed_at = j
                    break
            if confirmed_at is not None:
                in_position = True
                entry_idx = confirmed_at
                # fast-forward i to the confirmation bar; the loop's next
                # iteration will fall into the in_position branch and mark it
                i = confirmed_at
                position.iloc[i] = 1
                i += 1
                continue
        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
