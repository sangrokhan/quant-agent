"""Strategy: RSI(2) mean reversion gated by a STACKED volume-z-score + ATR%
low-vol filter pair.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per Ali Casey's StatOasis 15,552-backtest sweep of 80 volume/volatility
filters bolted onto Larry Connors' RSI(2)
(https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter),
the single best filter (ATR% below its own trailing 100-day median) is
already tested and accepted SPY-only in this repo (2026-09-20-140). The
source's own reliable-STACKED-pair table (>=15% signal coverage AND >=50%
of variants clearing the 50-trade reliability floor) flags a pair not yet
tried here: "Volume z-score above 1 + ATR% below its 100-day median" --
30.1% signals kept, profit factor 2.46 vs 1.70 unfiltered (+0.76, the
largest gain among reliable/covered stacked pairs), improved profit factor
in 97.6% of 96 matched pairings, drawdown -5.3pp vs unfiltered. This
iteration tests whether stacking that specific volume z-score condition ON
TOP of the already-accepted ATR% gate rescues the QQQ near-miss from
2026-09-20-140 (QQQ Sharpe 0.786, everything else passing) or extends
coverage, while remaining aware the source itself found stacking mostly
narrows the sample rather than compounding edge.

Signal logic
------------
- RSI(2) on close (Wilder-style, using simple rolling gain/loss averages).
- ATR% = ATR(atr_window) / close; gate = ATR% <= trailing atr_lookback-day
  rolling median (low-vol regime), per the already-accepted single-filter
  construction (2026-09-20-140).
- Volume z-score = (volume - rolling_mean(vol_window)) / rolling_std(vol_window);
  gate = z-score > vol_z_threshold (source's own "above 1" condition).
- Trend filter: close > SMA(200) (same uptrend gate as every other
  RSI(2) entry tested in this repo, e.g. 2026-09-03-005).
- Entry (long): close>SMA200 AND RSI(2)<entry_threshold AND ATR%-gate AND
  volume-z-score-gate, all simultaneously true on the same bar.
- Exit: RSI(2)>exit_threshold, OR a max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py): generate_signals/generate_returns both accept
price_df plus keyword params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    return rsi


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    entry_threshold: float = 5.0,
    exit_threshold: float = 70.0,
    max_hold_days: int = 10,
    rsi_window: int = 2,
    trend_window: int = 200,
    atr_window: int = 14,
    atr_lookback: int = 100,
    vol_window: int = 50,
    vol_z_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    rsi = _rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    atr = _atr(df, atr_window)
    atr_pct = atr / close
    atr_pct_median = atr_pct.rolling(atr_lookback, min_periods=atr_window).median()
    low_vol_gate = atr_pct <= atr_pct_median

    vol_mean = volume.rolling(vol_window).mean()
    vol_std = volume.rolling(vol_window).std()
    vol_zscore = (volume - vol_mean) / vol_std.replace(0, float("nan"))
    vol_gate = vol_zscore > vol_z_threshold

    entry = (
        uptrend.fillna(False)
        & (rsi < entry_threshold)
        & low_vol_gate.fillna(False)
        & vol_gate.fillna(False)
    )
    exit_signal = rsi > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
