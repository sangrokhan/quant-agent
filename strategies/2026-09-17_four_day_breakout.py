"""Strategy: Four-Day Breakout swing entry (Ken Calhoun, TASC Nov 2017 code / Oct 2017 article).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-145):
Ken Calhoun's "Swing Trading Four-Day Breakouts" (S&C Oct 2017, TradeStation
code republished TASC Nov 2017 Traders' Tips): a pattern of FOUR consecutive
"green" (close > open) daily candles signals strong sustained momentum
worth entering a breakout swing trade. Source's own disclosed TradeStation
strategy: after the 4-green-candle pattern completes, a buy-stop order is
armed at (highest high of those 4 bars + a small offset) and stays armed
for up to `max_bars_to_wait` bars; a dollar-trailing stop manages the exit.
Author's own rationale (per the article summary): "this pattern is
effective because it buys into strong momentum."

Adaptation for this repo's OHLCV-only, no-order-placement-code contract
(see SAFETY.md): the buy-stop-above-the-4-bar-high arming window becomes a
simple "if price breaks above the 4-bar high within breakout_expiry_bars
of pattern completion, enter long"; the source's dollar-trailing stop
(SetDollarTrailing) is replaced with a percentage trailing-stop-equivalent
exit -- close falling back below a rolling trail_window-day low from the
post-entry high-water mark -- plus a max_hold_days time-stop backstop
(both are our own additions, flagged as such, since fixed-dollar stops
aren't meaningfully comparable across QQQ/SPY/BTC/ETH price scales).

Source: https://traders.com/Documentation/FEEDbk_docs/2017/11/TradersTips.html
(TradeStation section, read via browser_exec).

This is a genuinely novel entry trigger for this repo: no prior strategy
requires exactly 4 consecutive green (close>open) candles as the setup,
nor an arm-then-breakout-above-the-pattern-high mechanism specifically off
that count (distinct from NR7-contraction breakouts, Marubozu breakouts,
Golden-Cross-confirmed breakouts, and ATR-expansion breakouts already
tested in this repo).

Interface contract for validators (see validation/validators.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    breakout_offset_pct: float = 0.001,
    breakout_expiry_bars: int = 2,
    trail_window: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    close = df["close"]

    green = close > open_
    pattern = green & green.shift(1).fillna(False) & green.shift(2).fillna(False) & green.shift(3).fillna(False)
    new_pattern = pattern & ~pattern.shift(1).fillna(False)

    pattern_high = high.rolling(4).max()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    high_water = None
    armed_bar = None
    buy_stop_price = None

    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            high_water = max(high_water, close.iloc[i])
            trail_stop_level = close.iloc[max(0, i - trail_window):i].min() if i > entry_idx else close.iloc[i]
            if close.iloc[i] < trail_stop_level or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                armed_bar = None
                continue
            position.iloc[i] = 1
        else:
            if bool(new_pattern.iloc[i]):
                armed_bar = i
                buy_stop_price = pattern_high.iloc[i] * (1 + breakout_offset_pct)

            if armed_bar is not None and (i - armed_bar) <= breakout_expiry_bars:
                if high.iloc[i] >= buy_stop_price:
                    in_position = True
                    entry_idx = i
                    high_water = close.iloc[i]
                    position.iloc[i] = 1
                    armed_bar = None
                else:
                    position.iloc[i] = 0
            else:
                armed_bar = None
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
