"""Strategy: intraday (open->close) reversal after an ATR-normalized overnight gap down, in an uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Source: QuantConnect community forum post "Mind the Gap: An Intraday Reversal
Strategy Using Gap Downs and ATR" by Robert Wiener (May 2025), itself derived
from a Quantitativo blog gap-down-reversal concept.
(https://www.quantconnect.com/forum/discussion/19075/mind-the-gap-an-intraday-reversal-strategy-using-gap-downs-and-atr/)
Source's own rule: universe = stocks above their 100-day SMA (uptrend
filter); entry at market open when the stock gaps down more than 1.2x its
14-day ATR relative to yesterday's close; exit 15 minutes after the open
(same-session, no overnight hold).

Daily-bar adaptation (this repo has no reliable minute-resolution intraday
data via data/loaders.py, so the "15 minutes after open" scalp is proxied by
the same trading day's open->close return -- the strategy is still a
same-day-only reversal trade, no overnight exposure):
- Uptrend filter: close > SMA(trend_window) (source uses 100; parameterized).
- Gap trigger: (prev_close - today_open) / ATR(atr_window) >= gap_atr_mult
  (source's own 1.2x multiplier is a default, swept in the grid).
- On a trigger day, the strategy is "long from today's open to today's
  close" -- i.e. it earns today's (close/open - 1) return, then is flat
  again for the rest of the sample. No multi-day holding.

This is distinct from every other gap strategy already tried in this repo:
all prior gap-fade/gap-fill entries use a FIXED PERCENTAGE gap threshold
(e.g. -0.15% to -0.6%) or a raw ATR(50)*0.5 absolute-price trigger measured
on the NEXT bar; this one normalizes the overnight gap size directly by a
*trailing ATR ratio* measured on entry day itself and trades ONLY the
open->close leg of the trigger day (no swing hold, no SMA-cross exit, no
time-stop) -- a materially different mechanical and holding-period
construction (see 2026-09-08-018 FVG entry and 2026-09-08-120 Gap-Down Long
for the closest priors, both rejected, both using next-bar entries and
multi-day holds).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume), returns the strategy's daily return series.

    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index
        (1 = long for that trading day's open->close leg, 0 = flat).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    atr_window: int = 14,
    gap_atr_mult: float = 1.2,
) -> pd.Series:
    df = _prep(price_df)

    sma_trend = df["close"].rolling(trend_window).mean()
    uptrend = df["close"].shift(1) > sma_trend.shift(1)  # confirmed trend as of yesterday's close

    tr = _true_range(df)
    atr = tr.rolling(atr_window).mean().shift(1)  # ATR known as of yesterday (no lookahead into today's range)

    prev_close = df["close"].shift(1)
    gap_down_atr = (prev_close - df["open"]) / atr

    trigger = (gap_down_atr >= gap_atr_mult) & uptrend & atr.notna() & (atr > 0)

    signal = trigger.astype(int)
    signal = signal.fillna(0).astype(int)
    signal.name = "position"
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    atr_window: int = 14,
    gap_atr_mult: float = 1.2,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(
        df, trend_window=trend_window, atr_window=atr_window, gap_atr_mult=gap_atr_mult
    )

    # Same-day open -> close return (proxy for the intraday scalp), only on
    # trigger days; zero otherwise (no overnight exposure at all).
    open_to_close = (df["close"] / df["open"]) - 1.0
    strat_returns = signal * open_to_close
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns
