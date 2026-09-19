"""Strategy: VIDYA (Variable Index Dynamic Average, Tushar Chande 1992) trend crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-073):
Per StonehillForex's "VIDYA As A Baseline Indicator" (browser_exec fallback --
web_search DDGS backend errored/returned mangled results this iteration), the
VIDYA is an adaptive moving average developed by Tushar Chande (1992,
Technical Analysis of Stocks & Commodities magazine) that scales its EMA
smoothing constant by market volatility -- specifically the magnitude of the
Chande Momentum Oscillator (CMO), NOT the Efficiency Ratio (KAMA, already
tested in this repo) or fractal dimension (FRAMA). This makes VIDYA more
responsive in trending/volatile conditions and flatter in quiet/choppy
conditions, via a genuinely distinct adaptivity mechanism from every other
adaptive-MA family already in this repo (0 prior VIDYA hits in
strategies_index.jsonl). The source's own disclosed rule (StonehillForex):
"Long = candle closes above VIDYA line, entry on open of next candle; Short =
candle closes below VIDYA line" with default settings Period=9. We adapt
this to a long-only close-based entry (no next-day-open modeling needed for
this repo's daily-bar backtest) on QQQ/SPY/BTC/ETH: long when close crosses
above VIDYA, flat when close crosses back below.

VIDYA formula (Chande, standard):
    CMO_t = 100 * (sum(up moves, period) - sum(down moves, period))
                  / (sum(up moves, period) + sum(down moves, period))
    alpha = 2 / (period + 1)
    VIDYA_t = alpha * |CMO_t/100| * close_t + (1 - alpha * |CMO_t/100|) * VIDYA_{t-1}

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _cmo(close: pd.Series, period: int = 9) -> pd.Series:
    diff = close.diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    up_sum = up.rolling(period).sum()
    down_sum = down.rolling(period).sum()
    denom = (up_sum + down_sum).replace(0, np.nan)
    cmo = 100.0 * (up_sum - down_sum) / denom
    return cmo.fillna(0.0)


def _vidya(close: pd.Series, period: int = 9) -> pd.Series:
    cmo = _cmo(close, period=period)
    alpha_base = 2.0 / (period + 1)
    k = alpha_base * cmo.abs() / 100.0

    vidya = pd.Series(index=close.index, dtype=float)
    first_valid = close.first_valid_index()
    vidya.loc[first_valid] = close.loc[first_valid]
    idx_list = list(close.index)
    start_pos = idx_list.index(first_valid)
    prev_val = close.loc[first_valid]
    for i in range(start_pos + 1, len(idx_list)):
        cur_idx = idx_list[i]
        k_val = k.loc[cur_idx] if pd.notna(k.loc[cur_idx]) else 0.0
        cur_close = close.loc[cur_idx]
        prev_val = k_val * cur_close + (1 - k_val) * prev_val
        vidya.loc[cur_idx] = prev_val
    return vidya


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 9,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close crosses above the VIDYA line AND close is above a
    longer-term trend SMA (avoids whipsaw in structural downtrends, since
    the source's own bare crossover rule had no regime filter disclosed
    beyond the indicator itself); exit on close crossing back below VIDYA.
    """
    df = _prep(price_df)
    close = df["close"]

    vidya = _vidya(close, period=period)
    trend_sma = close.rolling(trend_window).mean()

    above_vidya = close > vidya
    above_trend = close > trend_sma
    entry_ok = above_vidya & above_trend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if not bool(above_vidya.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_ok.iloc[i]):
                in_position = True
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
