"""Strategy: Renko-brick trend-following (long only), synthesizing Renko
bricks from daily close prices and trading consecutive-brick momentum with
a 2-brick reversal exit.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per SMC Global Securities' Renko chart guide
(https://www.smctradeonline.com/blog/stock-market/what-are-renko-charts):
Renko bricks are formed purely from price movement (a fixed `brick_size`),
filtering out time and small noise. Traditional Renko construction requires
a LARGER move (2x brick size) to print a reversal brick than to continue in
the same direction -- this asymmetry is what filters chop. The source's own
"Trend Following Strategy" section: enter in the direction of an
established trend once a new brick confirms continued momentum (i.e. after
`min_consecutive_bricks` same-direction bricks have printed). This is a
fundamentally new indicator family for this repo (0 prior Renko hits in
knowledge_base) and distinct from every existing ATR/Donchian/range-based
breakout entry here, because the entry/exit ladder is defined by a
synthetic brick sequence (with the asymmetric 2x-reversal rule) rather than
a raw price level, band, or fixed-bar range.

Signal logic (long side only)
------------------------------
- Bricks are synthesized from daily closes: `brick_size` is ATR-scaled
  (brick_atr_mult * ATR(atr_window)), recomputed once at the start of each
  backtest window using the full-series average ATR for stability (a
  Renko chart doesn't have per-bar changing brick size in practice).
- A new UP brick prints when close moves >= current_brick_top + brick_size
  from the last confirmed brick's price. A new DOWN brick (reversal from an
  uptrend) requires close to fall >= 2 * brick_size below the last brick's
  price (the source's asymmetric reversal rule); continuing DOWN bricks
  need only 1x brick_size once already in a downtrend, and symmetric logic
  applies from a downtrend back to up.
- Entry: after `min_consecutive_bricks` consecutive UP bricks have printed
  (trend confirmation), go long.
- Exit: a DOWN brick prints (2-brick-reversal invalidation) while long, or
  `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _renko_bricks(close: pd.Series, brick_size: float) -> pd.Series:
    """Return a per-bar signed brick-direction series: +1 per new up brick
    confirmed on that bar, -1 per new down brick, 0 if no new brick."""
    n = len(close)
    direction = pd.Series(0, index=close.index, dtype=int)
    if brick_size <= 0 or n == 0:
        return direction

    anchor = close.iloc[0]
    trend = 0  # 0=undetermined, 1=up, -1=down

    for i in range(n):
        price = close.iloc[i]
        if trend == 0:
            if price >= anchor + brick_size:
                trend = 1
                anchor = anchor + brick_size
                direction.iloc[i] = 1
            elif price <= anchor - brick_size:
                trend = -1
                anchor = anchor - brick_size
                direction.iloc[i] = -1
            continue

        if trend == 1:
            if price >= anchor + brick_size:
                anchor = anchor + brick_size
                direction.iloc[i] = 1
            elif price <= anchor - 2 * brick_size:
                trend = -1
                anchor = anchor - brick_size
                direction.iloc[i] = -1
        else:  # trend == -1
            if price <= anchor - brick_size:
                anchor = anchor - brick_size
                direction.iloc[i] = -1
            elif price >= anchor + 2 * brick_size:
                trend = 1
                anchor = anchor + brick_size
                direction.iloc[i] = 1

    return direction


def generate_signals(
    price_df: pd.DataFrame,
    brick_atr_mult: float = 1.0,
    atr_window: int = 14,
    min_consecutive_bricks: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    atr_series = _atr(df, atr_window)
    avg_atr = atr_series.dropna().mean()
    brick_size = float(avg_atr * brick_atr_mult) if pd.notna(avg_atr) and avg_atr > 0 else 0.0

    brick_dir = _renko_bricks(close, brick_size)

    position = pd.Series(0, index=close.index, dtype=int)
    if brick_size <= 0:
        return position

    in_position = False
    entry_idx = 0
    consecutive_up = 0

    for i in range(n):
        d = int(brick_dir.iloc[i])
        if d == 1:
            consecutive_up += 1
        elif d == -1:
            consecutive_up = 0

        if in_position:
            held = i - entry_idx
            if d == -1 or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if d == 1 and consecutive_up >= min_consecutive_bricks:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

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
