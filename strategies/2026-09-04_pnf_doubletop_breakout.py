"""Strategy: Point and Figure (P&F) chart double-top breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-143):
Point and Figure charts filter out time-based noise by plotting price
movement as columns of X's (rising) and O's (falling), only forming a new
column after price reverses by a fixed "reversal" number of "boxes" (a
box = a fixed price increment, sized as a fraction of the underlying
price, here computed via an ATR-derived box size so it adapts to the
instrument's volatility scale). Per Google's AI-overview synthesis of
Tradyom/Investopedia/TradeAlgo P&F explainers, the canonical "Double Top
Breakout" buy signal fires when a new rising X-column exceeds the highest
box of the immediately preceding X-column (classic P&F breakout, filters
noise via the box/reversal construction itself rather than a lookback
window); the mirror Double Bottom Breakdown fires the exit/sell when an
O-column falls one box below the prior O-column's low. This is the first
Point-and-Figure (time-independent box-and-reversal charting) strategy
tried in this repo -- distinct from the already-tested Renko (also
box-based but without the double-top/bottom column-comparison breakout
rule), Kagi (percentage-reversal threshold, no discrete box grid), and
three-line-break constructions.

Signal logic
------------
- box_size = ATR(atr_window) * box_atr_mult (adaptive box sizing).
- Convert close price series into a discrete P&F column sequence: track a
  running "current column" (X-rising or O-falling) and its high/low in box
  units; flip column direction only when price reverses by
  >= reversal_boxes * box_size from the current column's extreme.
- Track each completed column's high (for X columns) / low (for O columns).
- Entry (long): when the CURRENT (still-forming) X-column's running high
  exceeds the immediately preceding completed X-column's high (double-top
  breakout).
- Exit: when the CURRENT (still-forming) O-column's running low falls
  below the immediately preceding completed O-column's low (double-bottom
  breakdown), OR a max_hold_days time-stop backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

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
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    box_atr_mult: float = 0.5,
    reversal_boxes: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on P&F double-top/bottom breakout."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(high, low, close, atr_window)
    n = len(close)

    position = pd.Series(0, index=close.index, dtype=int)

    # P&F state machine
    box_size = None
    direction = None  # "X" or "O"
    col_extreme = None  # running high (X) or low (O) of current column, in price terms
    prev_completed_high = None  # last completed X-column's high
    prev_completed_low = None  # last completed O-column's low
    in_position = False
    entry_idx = 0

    warmup = max(atr_window, 5)
    for i in range(n):
        if i < warmup or pd.isna(atr.iloc[i]) or atr.iloc[i] <= 0:
            position.iloc[i] = 1 if in_position else 0
            continue

        bs = atr.iloc[i] * box_atr_mult
        if bs <= 0:
            position.iloc[i] = 1 if in_position else 0
            continue

        price = close.iloc[i]

        if direction is None:
            # initialize
            direction = "X"
            col_extreme = price
            box_size = bs
        else:
            box_size = bs  # allow adaptive box size to drift with vol
            if direction == "X":
                if price > col_extreme:
                    col_extreme = price
                elif price <= col_extreme - reversal_boxes * box_size:
                    # reversal: complete X column, start O column
                    prev_completed_high = col_extreme
                    direction = "O"
                    col_extreme = price
            else:  # direction == "O"
                if price < col_extreme:
                    col_extreme = price
                elif price >= col_extreme + reversal_boxes * box_size:
                    # reversal: complete O column, start X column
                    prev_completed_low = col_extreme
                    direction = "X"
                    col_extreme = price

        # Entry: current X column's running high exceeds prior completed X-column high
        entry_signal = (
            direction == "X"
            and prev_completed_high is not None
            and col_extreme > prev_completed_high
        )
        # Exit: current O column's running low falls below prior completed O-column low
        exit_signal = (
            direction == "O"
            and prev_completed_low is not None
            and col_extreme < prev_completed_low
        )

        if in_position:
            held = i - entry_idx
            if exit_signal or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if entry_signal:
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
