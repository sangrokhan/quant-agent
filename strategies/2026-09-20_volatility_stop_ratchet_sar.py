"""Strategy: Volatility Stop (ATR-ratchet stop-and-reverse, always-in-market).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://senzoukria.com/indicators/volatility-stop ("Volatility Stop
Indicator: Formula, Settings and How to Read It", the "modern transposition"
of J. Welles Wilder's 1978 Volatility System): a single trailing ATR-ratchet
stop line that NEVER retreats while a trend side holds, and flips to the
opposite side (stop-and-reverse, always in the market -- no flat state) the
instant a close breaks it. This is deliberately distinct from this repo's
existing Wilder Volatility System entry (id 2026-09-08-011, oxfordstrat.com
source), which is a LONG-ONLY adaptation using a rolling-low breakout entry
+ SIC-ARC trailing stop with a flat state and a fixed 6x-ATR hard stop. This
strategy instead:
  (1) is always in the market (long OR short, never flat) -- a genuinely
      different exposure profile,
  (2) seeds the very first ATR-defined bar directly (long if close>=open
      else short) rather than requiring a breakout trigger to enter,
  (3) uses a strict one-sided ratchet (max for long / min for short) with
      no separate hard stop-loss layer,
  (4) breaks are tested against the PREVIOUS bar's stop value (not the
      current bar's), and equality (close == stop) does NOT count as a
      break -- both exact conventions per the source.

Formula (as implemented per source, using standard Wilder-style ATR, not
the source's own smoothing convention which wasn't fully specified beyond
"ATR"):
    Seed at first bar where ATR is defined (i = atr_period):
        trend[i] = LONG if close[i] >= open[i] else SHORT
        stop[i]  = close[i] - mult*ATR[i]   if LONG
                 = close[i] + mult*ATR[i]   if SHORT
    For each subsequent bar i:
        if trend[i-1] == LONG:
            if close[i] < stop[i-1]:               # break (strict)
                trend[i] = SHORT; stop[i] = close[i] + mult*ATR[i]
            else:
                trend[i] = LONG
                stop[i] = max(stop[i-1], close[i] - mult*ATR[i])  # ratchet
        else:  # trend[i-1] == SHORT (mirror)
            if close[i] > stop[i-1]:
                trend[i] = LONG; stop[i] = close[i] - mult*ATR[i]
            else:
                trend[i] = SHORT
                stop[i] = min(stop[i-1], close[i] + mult*ATR[i])

Position is +1 while LONG, -1 while SHORT (always in the market once ATR
warms up). Defaults per source: atr_period=14, mult=3.0 (Wilder's own
approximate distance).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({-1, 1} once warmed
        up; 0 during the ATR warm-up window only)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    """Resample to daily bars if the input looks intraday (crypto loader
    default is hourly) -- this strategy's ATR-ratchet logic is designed for
    daily bars per the source."""
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    prior_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prior_close).abs(),
            (df["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(df: pd.DataFrame, atr_period: int) -> pd.Series:
    tr = _true_range(df)
    # Wilder's smoothing (RMA), standard for ATR.
    return tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 14,
    mult: float = 3.0,
) -> pd.Series:
    """Return a {-1, 0, 1} position series (0 only during ATR warm-up)."""
    df = _prep(price_df)
    close = df["close"].values
    open_ = df["open"].values
    atr = _atr(df, atr_period).values
    n = len(close)

    position = np.zeros(n, dtype=int)
    stop = np.full(n, np.nan)

    first_valid = None
    for i in range(n):
        if not np.isnan(atr[i]):
            first_valid = i
            break
    if first_valid is None:
        return pd.Series(position, index=df.index)

    # Seed.
    i = first_valid
    if close[i] >= open_[i]:
        position[i] = 1
        stop[i] = close[i] - mult * atr[i]
    else:
        position[i] = -1
        stop[i] = close[i] + mult * atr[i]

    for i in range(first_valid + 1, n):
        prev_trend = position[i - 1]
        prev_stop = stop[i - 1]
        if prev_trend == 1:
            if close[i] < prev_stop:
                position[i] = -1
                stop[i] = close[i] + mult * atr[i]
            else:
                position[i] = 1
                stop[i] = max(prev_stop, close[i] - mult * atr[i])
        else:  # prev_trend == -1 (mirror)
            if close[i] > prev_stop:
                position[i] = 1
                stop[i] = close[i] - mult * atr[i]
            else:
                position[i] = -1
                stop[i] = min(prev_stop, close[i] + mult * atr[i])

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's state determines today's exposure
    # (avoid look-ahead -- can't trade on today's own close, which is what
    # determines today's flip).
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
