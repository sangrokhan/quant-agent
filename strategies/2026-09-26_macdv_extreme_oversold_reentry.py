"""Strategy: MACD-V extreme-oversold ("Risk" zone) mean-reversion re-entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-070):
Per https://chartschool.stockcharts.com/.../macd-v (Alex Spiroglou 2022),
MACD-V's disclosed "seven core momentum stages" table gives exact numeric
thresholds. The extreme "Risk (oversold)" zone is defined as MACD-V < -150
-- the market is at risk of a sharp reversal from an extreme oversold
momentum reading. This is DISTINCT from this repo's 3 prior MACD-V entries:
Rebounding-zone signal-line crossover (2026-09-06-094, -150<MACD-V<50 above
signal), Rallying-zone breakout (2026-09-12-155, 50<MACD-V<150 above
signal), and the continuous-sizing dial (2026-09-14-141) -- none of those
uses the -150 extreme threshold itself as an entry trigger. Here the entry
fires specifically when MACD-V exits the extreme Risk-oversold zone (crosses
back above -150 from below), betting on a mean-reversion rebound from an
extreme momentum trough, gated by an established uptrend filter to avoid
catching falling knives in structural downtrends.

Signal logic
------------
- MACD-V = [(EMA12 - EMA26) / ATR(26)] * 100 (volatility-normalized MACD,
  per source's own formula).
- Entry (long): MACD-V crosses back above the extreme oversold threshold
  (-150) from below AND close > SMA(trend_window) (only trade the rebound
  inside an established uptrend, not a standalone reversal call).
- Exit: MACD-V re-enters the extreme zone (crosses back below -150,
  invalidating the rebound thesis), OR MACD-V rises into/through the
  Risk-overbought zone (crosses above overbought_level=150, take profit),
  OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    return tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()


def _macd_v(df: pd.DataFrame, fast: int, slow: int, atr_window: int) -> pd.Series:
    close = df["close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    atr = _atr(df, atr_window)
    macd_v = ((ema_fast - ema_slow) / atr.replace(0.0, 1e-12)) * 100.0
    return macd_v


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 12,
    slow_window: int = 26,
    atr_window: int = 26,
    oversold_level: float = -150.0,
    overbought_level: float = 150.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_v = _macd_v(df, fast_window, slow_window, atr_window)
    sma_trend = close.rolling(trend_window).mean()

    macd_v_prev = macd_v.shift(1)
    exit_oversold_up = (macd_v > oversold_level) & (macd_v_prev <= oversold_level)
    entry = exit_oversold_up & (close > sma_trend)

    exit_reenter_oversold = (macd_v < oversold_level) & (macd_v_prev >= oversold_level)
    exit_overbought = (macd_v > overbought_level) & (macd_v_prev <= overbought_level)

    entry = entry.fillna(False)
    exit_reenter_oversold = exit_reenter_oversold.fillna(False)
    exit_overbought = exit_overbought.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_reenter_oversold.iloc[i]) or bool(exit_overbought.iloc[i]) or held >= max_hold_days:
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
