"""Strategy: John Carter's TTM Scalper indicator (from "Mastering the
Trade"), long-only swing-reversal-confirmation trend-following.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per HPotter's exact disclosed Pine v2 source (John Carter's TTM Scalper
indicator, https://www.tradingview.com/script/CddpDBGA-TTM-scalper-indicator-Strategy/,
found via web_search this iteration): a pure price-action swing-reversal-
confirmation pattern using only the last 4 closes (no smoothing, no
indicator inputs):

    trigger_sell = (close[1] < close) AND (close[2] < close[1] OR close[3] < close[1])
    trigger_buy  = (close[1] > close) AND (close[2] > close[1] OR close[3] > close[1])

`trigger_sell` fires when the latest bar closed up from the prior close,
but a bar 2-3 periods back was still lower than that prior close -- Carter's
own disclosed pattern for confirming an UP-swing has exhausted (a local
top, hence "sell"). `trigger_buy` is the mirror: confirms a DOWN-swing has
exhausted (a local bottom, "buy"). A state machine (`buy_sell_switch`)
tracks which trigger fired most recently, flipping the position direction
(long after a buy-trigger confirmation, flat/short after a sell-trigger
confirmation) -- "the squares are not real-time but will show up once the
third bar has confirmed a reversal" per the source's own note.

Implemented long-only per this repo's convention: long while the state
machine is in its "buy" (green) state, flat while in its "sell" (red)
state. First TTM Scalper strategy in this repo -- distinct from all
TTM Squeeze/TTM Trend entries already tested (a different member of Carter's
"TTM" indicator family, this one a pure close-price swing-reversal pattern
with zero smoothing or parameters beyond the lookback itself).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ttm_scalper_position(
    close: pd.Series, trend_window: int, use_trend_gate: bool
) -> pd.Series:
    c = close.to_numpy()
    n = len(c)

    trigger_sell = np.zeros(n, dtype=bool)
    trigger_buy = np.zeros(n, dtype=bool)
    for i in range(3, n):
        # close[1] < close[0] (pine convention: close[1]=prior bar, close=current)
        up_move = c[i - 1] < c[i]
        down_move = c[i - 1] > c[i]
        confirm_sell = (c[i - 2] < c[i - 1]) or (c[i - 3] < c[i - 1])
        confirm_buy = (c[i - 2] > c[i - 1]) or (c[i - 3] > c[i - 1])
        trigger_sell[i] = up_move and confirm_sell
        trigger_buy[i] = down_move and confirm_buy

    buy_sell_switch = np.zeros(n, dtype=bool)  # True = "sell state" (per pine's boolean semantics)
    pos = np.zeros(n)  # +1 = green/long, -1 = red/flat-or-short
    for i in range(1, n):
        prev_switch = buy_sell_switch[i - 1]
        if trigger_sell[i]:
            buy_sell_switch[i] = True
        elif trigger_buy[i]:
            buy_sell_switch[i] = False
        else:
            buy_sell_switch[i] = prev_switch

        if trigger_sell[i] and not prev_switch:
            pos[i] = -1.0  # red (sell/top confirmed)
        elif trigger_buy[i] and prev_switch:
            pos[i] = 1.0  # green (buy/bottom confirmed)
        else:
            pos[i] = pos[i - 1]

    position = pd.Series((pos == 1.0).astype(float), index=close.index)

    if use_trend_gate:
        trend_long = close > close.rolling(trend_window).mean()
        position = position.where(trend_long.fillna(False), other=0.0)

    return position


def generate_signals(
    price_df: pd.DataFrame,
    use_trend_gate: bool = False,
    trend_window: int = 40,
) -> pd.Series:
    """0/1 long-only position series per Carter's TTM Scalper reversal
    confirmation state machine, optionally gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]
    return _ttm_scalper_position(close, trend_window, use_trend_gate)


def generate_returns(
    price_df: pd.DataFrame,
    use_trend_gate: bool = False,
    trend_window: int = 40,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, use_trend_gate=use_trend_gate, trend_window=trend_window
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
