"""Strategy: CAM (Coordinated ADX and MACD) trend regime signal (Barbara Star, TASC Jan 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-147):
Barbara Star's TASC Jan 2018 article "The CAM Indicator For Trends And
Countertrends" introduces a simple 2x2 state machine classifying each bar
by whether ADX(10) is rising AND whether MACD(12,26) is rising:
    ADX rising & MACD rising      -> "CAM UP"   (confirmed uptrend)
    ADX rising & MACD NOT rising  -> "CAM DN"   (confirmed downtrend)
    ADX NOT rising & MACD rising  -> "CAM CT"   (countertrend rally)
    ADX NOT rising & MACD NOT rising -> "CAM PB" (pullback / consolidation)
Source's own rationale: ADX rising confirms trend STRENGTH is increasing
(regardless of direction), while MACD rising signals price MOMENTUM is
turning bullish -- combining both flags identifies whether a directional
move is a confirmed trend (both agree) or a fragile pullback/countertrend
(they disagree). Source presents CAM purely as a chart-painting/labeling
indicator (color-coded bars, RadarScreen text) with no disclosed trading
rule -- the article "also suggests using other indicators such as an EMA
and CCI to help confirm signals."

This is a novel indicator combination for this repo: no prior strategy
gates entries on the joint (ADX-rising, MACD-rising) 2x2 state -- prior
ADX-family entries (34+) use ADX level or ADX-rising alone as a trend-
strength confirmation gate for a SEPARATE trigger, never paired with
"MACD rising" (not MACD crossover/level, specifically its own slope) in
this exact 2-condition state machine.

Our own addition (flagged as such, source gives no trading rule): long
entry when the bar transitions INTO the "CAM UP" state (both ADX and MACD
newly rising together, i.e. the regime just confirmed); exit when the
state leaves CAM UP (either ADX or MACD stops rising) or a max_hold_days
time-stop. An optional EMA trend filter (close > EMA(ema_trend_window)) is
included per the source's own suggestion to use an EMA for signal
confirmation.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/01/TradersTips.html
(TradeStation section, read via browser_exec).

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


def _macd(close: pd.Series, fast: int, slow: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


def _adx(df: pd.DataFrame, length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / length, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / length, adjust=False).mean() / atr.replace(0, float("nan"))
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / length, adjust=False).mean() / atr.replace(0, float("nan"))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx = dx.ewm(alpha=1.0 / length, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    adx_length: int = 10,
    macd_fast: int = 12,
    macd_slow: int = 26,
    ema_trend_window: int = 0,  # 0 disables the optional EMA trend filter
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    adx_val = _adx(df, adx_length)
    macd_val = _macd(close, macd_fast, macd_slow)

    adx_rising = adx_val > adx_val.shift(1)
    macd_rising = macd_val > macd_val.shift(1)

    cam_up = adx_rising.fillna(False) & macd_rising.fillna(False)
    entry = cam_up & ~cam_up.shift(1).fillna(False)

    if ema_trend_window > 0:
        ema_trend = close.ewm(span=ema_trend_window, adjust=False).mean()
        entry = entry & (close > ema_trend)

    exit_state_leave = ~cam_up

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_state_leave.iloc[i]) or held >= max_hold_days:
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
