"""Strategy: ZigZag Higher-High/Higher-Low swing pivot trend continuation
(long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per the ZigZag indicator's standard construction (deviation-filtered swing
pivots, per Google AI-overview synthesis of LuxAlgo/TradingView/PineTrades/
ThinkMarkets/Investopedia), a ZigZag leg confirms a new pivot only once
price reverses by >= deviation_pct from the prior extreme. When the most
recently confirmed pivot sequence forms a Higher-High followed by a
Higher-Low (a classic uptrend structure confirmation), buying on the bar
immediately after the Higher-Low pivot locks in captures trend continuation
momentum with a defined risk (stop below the swing low, per source's own
numeric rule: swing low - 1*ATR(14)). Take-profit at 2x the initial risk
(2:1 R:R, per source) or the prior confirmed swing high, whichever the
strategy's exit-first design reaches first (we use the take-profit price
level, not requiring exact bar-level target-hit precision beyond a daily
close crossing it, since this repo's vectorbt-based grid/validators operate
on daily-bar close data, not intrabar fills).

First ZigZag-indicator strategy in this knowledge base (8 prior "ZigZag"
keyword matches in strategies_index.jsonl are for an UNRELATED indicator
family per manual check -- none use this deviation-filtered
HH/HL-swing-structure entry logic).

Sources read this iteration:
- Google AI-overview synthesis of ZigZag indicator numeric strategy rules
  (LuxAlgo, TradingView, PineTrades, ThinkMarkets, Investopedia).

Signal logic
------------
- ZigZag pivot detection: track running extremes; confirm a new pivot only
  when price reverses by >= deviation_pct from the last confirmed pivot
  (standard ZigZag deviation-filter construction).
- Track the last two confirmed pivot types/prices. A confirmed sequence of
  [swing low, swing high, swing low] where the second swing low > the
  first swing low (Higher Low following a prior Higher High) triggers a
  long entry on the bar the second swing low is confirmed.
- Stop-loss: confirmed swing low - atr_mult * ATR(14).
- Take-profit: entry + reward_risk_mult * (entry - stop_loss), i.e. a fixed
  R-multiple target.
- Exit: close crosses below stop OR close crosses above take-profit OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _zigzag_pivots(close: pd.Series, deviation_pct: float):
    """Returns a list of (index_position, price, kind) for confirmed
    ZigZag pivots, kind in {'high', 'low'}. Simple deviation-filter
    reconstruction (not a library implementation)."""
    n = len(close)
    pivots = []
    if n == 0:
        return pivots

    last_pivot_idx = 0
    last_pivot_price = close.iloc[0]
    # direction: None until first move confirmed; +1 tracking up, -1 tracking down
    direction = None
    extreme_idx = 0
    extreme_price = close.iloc[0]

    for i in range(1, n):
        p = close.iloc[i]
        if direction is None:
            change = (p - last_pivot_price) / last_pivot_price
            if abs(change) >= deviation_pct:
                direction = 1 if change > 0 else -1
                extreme_idx, extreme_price = i, p
            continue

        if direction == 1:
            if p > extreme_price:
                extreme_idx, extreme_price = i, p
            else:
                retrace = (extreme_price - p) / extreme_price
                if retrace >= deviation_pct:
                    pivots.append((extreme_idx, extreme_price, "high"))
                    last_pivot_idx, last_pivot_price = extreme_idx, extreme_price
                    direction = -1
                    extreme_idx, extreme_price = i, p
        else:
            if p < extreme_price:
                extreme_idx, extreme_price = i, p
            else:
                retrace = (p - extreme_price) / extreme_price
                if retrace >= deviation_pct:
                    pivots.append((extreme_idx, extreme_price, "low"))
                    last_pivot_idx, last_pivot_price = extreme_idx, extreme_price
                    direction = 1
                    extreme_idx, extreme_price = i, p

    return pivots


def generate_signals(
    price_df: pd.DataFrame,
    deviation_pct: float = 0.05,
    atr_mult: float = 1.0,
    reward_risk_mult: float = 2.0,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, 14)

    pivots = _zigzag_pivots(close, deviation_pct)

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)

    # Build set of "entry trigger" bar indices: a confirmed [low, high, low]
    # sequence where the 2nd low > the 1st low (Higher Low after Higher High).
    entry_bars = {}
    for k in range(2, len(pivots)):
        idx2, price2, kind2 = pivots[k]
        idx1, price1, kind1 = pivots[k - 1]
        idx0, price0, kind0 = pivots[k - 2]
        if kind0 == "low" and kind1 == "high" and kind2 == "low" and price2 > price0:
            entry_bars[idx2] = (price2,)  # swing low price at confirmation

    in_position = False
    hold_days = 0
    stop_price = None
    tp_price = None

    for i in range(n):
        c = close.iloc[i]

        if in_position:
            hold_days += 1
            if c <= stop_price or c >= tp_price or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                stop_price = None
                tp_price = None
            else:
                position.iloc[i] = 1
                continue

        if i in entry_bars and not pd.isna(atr.iloc[i]):
            swing_low_price = entry_bars[i][0]
            stop = swing_low_price - atr_mult * atr.iloc[i]
            risk = c - stop
            if risk > 0:
                in_position = True
                hold_days = 1
                stop_price = stop
                tp_price = c + reward_risk_mult * risk
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    deviation_pct: float = 0.05,
    atr_mult: float = 1.0,
    reward_risk_mult: float = 2.0,
    max_hold_days: int = 30,
    leverage_cap: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        deviation_pct=deviation_pct,
        atr_mult=atr_mult,
        reward_risk_mult=reward_risk_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0) * leverage_cap
    return strat_returns
