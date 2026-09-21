"""Strategy: Wilder's Commodity Selection Index (CSI) as a trend-strength gate.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.prorealcode.com/prorealtime-indicators/wilders-csi-commodity-selection-index/
(J. Welles Wilder, "New Concepts in Technical Trading Systems"), the
Commodity Selection Index combines trend strength (ADXR) with normalized
volatility (a balanced/normalized ATR) into a single "tradeability" score:

    TRbalanced = 100 * max(range/close[1], |high-close[1]|/close[1],
                            |low-close[1]|/close[1])
    ATRbalanced = SMA(TRbalanced, period)
    CSI = ADXR(period) * ATRbalanced

Wilder's original use (per https://forex-indicators.net/trend-indicators/commodity-selection-index)
is a CROSS-SECTIONAL ranking across multiple commodities to decide WHICH to
trade -- infeasible with this repo's single-symbol interface. This is a
time-series adaptation: use CSI's OWN rolling percentile rank (relative to
its own trailing history) as a trend-strength+volatility regime gate for a
simple SMA trend-following entry, on the theory that Wilder's own claim
("a high CSI rating demonstrates the commodity has strong volatility
characteristics and is trending") should also identify favorable REGIMES
for a single asset over time, not just favorable assets cross-sectionally.
First Commodity Selection Index strategy in this repo -- distinct from the
already-tested/accepted plain-ADXR continuous-sizing-dial (2026-09-16-054)
since CSI multiplies ADXR by a SEPARATE normalized-volatility factor,
producing a fundamentally different (and typically much more skewed)
distribution than ADXR alone.

Signal logic
------------
- Trend gate: close > SMA(trend_window).
- Regime gate: CSI's own rolling percentile rank (over csi_lookback bars)
  >= csi_percentile_threshold (i.e., CSI itself is unusually high relative
  to its own trailing history for this asset -- "tradeable" regime).
- Entry (long): both gates true.
- Exit: either gate turns false, or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adxr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, 1e-12)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, 1e-12)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, 1e-12)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    adxr = (adx + adx.shift(period)) / 2.0
    return adxr


def _csi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
    mm: int = 3,
) -> pd.Series:
    prev_close = close.shift(1)
    price_range = high - low
    a = price_range / prev_close
    b = (high - prev_close).abs() / prev_close
    c = (low - prev_close).abs() / prev_close
    tr_balanced = 100.0 * pd.concat([a, b, c], axis=1).max(axis=1)
    atr_balanced = tr_balanced.rolling(mm).mean()

    adxr = _adxr(high, low, close, period)
    csi = adxr * atr_balanced
    return csi


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 14,
    mm: int = 3,
    trend_window: int = 40,
    csi_lookback: int = 126,
    csi_percentile_threshold: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    csi = _csi(high, low, close, period, mm)
    csi_pct_rank = csi.rolling(csi_lookback).rank(pct=True)
    csi_regime_ok = (csi_pct_rank >= csi_percentile_threshold).fillna(False)

    sma = close.rolling(trend_window).mean()
    trend_ok = (close > sma).fillna(False)

    entry_trigger = trend_ok & csi_regime_ok
    exit_trigger = ~(trend_ok & csi_regime_ok)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
