"""Strategy: Chande Trend Meter (CTM) composite trend-strength crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-033):
Per StockCharts ChartSchool's Chande Trend Meter (CTM, Tushar Chande,
visited this iteration -- https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chande-trend-meter-ctm):
CTM distills several technical readings into a single 0-100 composite
trend-strength score: (1) the close's %B position relative to Bollinger
Bands across FOUR timeframes (20/50/75/100-day), (2) the price change
relative to its own 100-day standard deviation, (3) the 14-day RSI, and
(4) whether a short-term (2-day) price-channel breakout just occurred.
Source's own scale: 90-100 very strong uptrend, 80-90 strong uptrend,
60-80 weak uptrend, 20-60 flat/weak downtrend, 0-20 strong downtrend;
source's own suggested scan is "CTM crosses above 60".

This repo already tested a DIFFERENT, simpler Chande indicator
(TrendScore, 2026-09-06-103 -- a +/-10 sign-comparison momentum score with
no Bollinger/RSI/breakout composite), so CTM is a genuinely distinct,
first-time-tested indicator family in this repo despite sharing Chande's
name. Hypothesis: a long entry when the composite CTM score crosses above
entry_threshold (source's own 60) signals a confirmed uptrend worth
trading; exit when CTM falls back below exit_threshold (source's own
20-60 "flat/weak downtrend" boundary, tested at 40/50).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pct_b(close: pd.Series, window: int, num_std: float = 2.0) -> pd.Series:
    """Bollinger %B: 0 = at lower band, 1 = at upper band (clipped to [0,1])."""
    sma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    pct_b = (close - lower) / (upper - lower).replace(0.0, float("nan"))
    return pct_b.clip(0.0, 1.0)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _compute_ctm(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    # (1) %B across 4 timeframes -> average, in [0,1]
    bb_component = pd.concat(
        [_pct_b(close, w) for w in (20, 50, 75, 100)], axis=1
    ).mean(axis=1)

    # (2) price change relative to its own 100-day std dev -> squashed to [0,1]
    std100 = close.rolling(100).std()
    price_chg_z = (close - close.shift(100)) / std100.replace(0.0, float("nan"))
    z_component = (price_chg_z / 4.0 + 0.5).clip(0.0, 1.0)  # +/-2 std maps to 0/1

    # (3) RSI(14), already 0-100 -> to [0,1]
    rsi_component = (_rsi(close, 14) / 100.0).clip(0.0, 1.0)

    # (4) 2-day price-channel breakout: +1 if new 2-day high, 0 if new 2-day
    # low, 0.5 otherwise
    ch_high = high.shift(1).rolling(2).max()
    ch_low = low.shift(1).rolling(2).min()
    breakout_component = pd.Series(0.5, index=close.index)
    breakout_component = breakout_component.where(close <= ch_high, 1.0)
    breakout_component = breakout_component.where(close >= ch_low, 0.0)

    composite = (bb_component + z_component + rsi_component + breakout_component) / 4.0
    ctm = (composite * 100.0).clip(0.0, 100.0)
    return ctm


def generate_signals(
    price_df: pd.DataFrame,
    entry_threshold: float = 60.0,
    exit_threshold: float = 40.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry when CTM crosses above entry_threshold; exit when CTM falls
    back below exit_threshold or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    ctm = _compute_ctm(df)

    entry_signal = (ctm >= entry_threshold) & (ctm.shift(1) < entry_threshold)
    exit_signal = ctm < exit_threshold

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    pos_vals = []
    for i in range(len(df)):
        if in_pos:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
        if not in_pos and bool(entry_signal.iloc[i]):
            in_pos = True
            hold_count = 0
        pos_vals.append(1 if in_pos else 0)
    position = pd.Series(pos_vals, index=df.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
