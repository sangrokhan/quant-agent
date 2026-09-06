"""Strategy: Renko chart Bollinger Band breakout (long-only trend-following).

Hypothesis (see knowledge_base/strategies_log.jsonl):
FXOpen's "Renko With Bollinger Bands Strategy" combines ATR-sized Renko
brick reconstruction (which strips time-axis noise, only registering moves
of at least `brick_size`) with Bollinger Bands computed on the Renko brick
series itself: "The strategy typically calls for observing two ... con-
secutive Renko brick closes outside the Bollinger Bands" as an entry
signal for capitalizing on strong, sustained trend moves once volatility
(band width) has widened. We operationalize the long side: reconstruct an
ATR-sized Renko brick series from daily closes; compute Bollinger Bands
(bb_window, bb_std -- source recommends 1.5 std vs the traditional 2.0 "to
sharpen the focus on volatility shifts") on the brick closes; long entry
when `confirm_bricks` (default 2) consecutive up-bricks close above the
upper Bollinger Band; exit on the first down-brick (source's take-profit
rule: "take profit after one or two bricks of the opposite colour appear")
or a max_hold_days time-stop.

Source: https://fxopen.com/blog/en/renko-trading-strategies-how-to-trade-with-renko-charts/
("Renko With Bollinger Bands Strategy" section, read in-browser).

First Renko+Bollinger-Band strategy in this repo -- distinct from the
already-rejected pure ATR-brick trend-follow (2026-09-04-086, brick-count
after a down-brick sequence with a 200-SMA filter, no Bollinger Bands),
its ADX-gated fix attempt (2026-09-04-087), Point & Figure double-top
breakout (2026-09-04-143, X/O columns not Renko bricks), and Three Line
Break (2026-09-05-040, variable-length lines not fixed-size bricks) since
this is the first to combine the Renko reconstruction with a volatility-
band (Bollinger) breakout confirmation rather than a pure brick-count or
box/line reversal rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _build_renko(close: pd.Series, brick_size: pd.Series) -> pd.DataFrame:
    """Reconstruct a Renko brick series from a daily close series and a
    (possibly time-varying, ATR-based) brick size. Returns a DataFrame
    indexed by the ORIGINAL bar at which each brick close is registered
    (the first bar where a new brick's threshold was crossed), with columns
    ``brick_close`` (the resulting Renko brick close level) and
    ``direction`` (+1 up-brick, -1 down-brick). Bars that do not complete a
    new brick carry forward the last known brick_close/direction (ffill).
    """
    n = len(close)
    c = close.to_numpy(dtype=float)
    bs = brick_size.to_numpy(dtype=float)

    brick_close = np.full(n, np.nan)
    direction = np.full(n, 0.0)

    # seed with the first valid brick_size bar
    start = 0
    while start < n and (np.isnan(bs[start]) or bs[start] <= 0):
        start += 1
    if start >= n:
        return pd.DataFrame(
            {"brick_close": brick_close, "direction": direction}, index=close.index
        )

    last_brick = c[start]
    last_dir = 0
    brick_close[start] = last_brick
    direction[start] = 0

    for i in range(start + 1, n):
        size = bs[i]
        if np.isnan(size) or size <= 0:
            brick_close[i] = last_brick
            direction[i] = last_dir
            continue
        diff = c[i] - last_brick
        num_bricks = int(diff // size) if diff >= 0 else -int((-diff) // size)
        if num_bricks != 0:
            last_brick = last_brick + num_bricks * size
            last_dir = 1 if num_bricks > 0 else -1
        brick_close[i] = last_brick
        direction[i] = last_dir

    return pd.DataFrame(
        {"brick_close": brick_close, "direction": direction}, index=close.index
    )


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    brick_atr_mult: float = 1.0,
    bb_window: int = 20,
    bb_std: float = 1.5,
    confirm_bricks: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    atr = _atr(df, atr_window)
    brick_size = atr * brick_atr_mult
    renko = _build_renko(close, brick_size)
    brick_close = renko["brick_close"]
    direction = renko["direction"]

    bb_mid = brick_close.rolling(bb_window).mean()
    bb_std_val = brick_close.rolling(bb_window).std()
    bb_upper = bb_mid + bb_std * bb_std_val

    above_upper = brick_close > bb_upper
    up_brick = direction > 0
    confirm_ok = (above_upper & up_brick).rolling(confirm_bricks).sum() >= confirm_bricks

    long_trigger = confirm_ok & (~confirm_ok.shift(1).fillna(False))
    exit_trigger = direction < 0  # first down-brick after entry

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    brick_atr_mult: float = 1.0,
    bb_window: int = 20,
    bb_std: float = 1.5,
    confirm_bricks: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        atr_window=atr_window,
        brick_atr_mult=brick_atr_mult,
        bb_window=bb_window,
        bb_std=bb_std,
        confirm_bricks=confirm_bricks,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
