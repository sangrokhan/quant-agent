"""Strategy: AMD (Accumulation-Manipulation-Distribution) POC Trade Setup,
adapted from intraday to daily bars.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per LuxAlgo's "AMD POC Trade Setup" indicator
(https://www.luxalgo.com/library/indicator/amd-poc-trade-setup, published
Sep 23 2026, read this iteration via browser_exec -- web_search DDGS/Yahoo
backend TLS-erroring on queries attempted this iteration), the classic
Accumulation-Manipulation-Distribution market-structure framework: (1) a
tight consolidation ("accumulation") range forms over N bars, (2) within
that range a volume profile locates the Point of Control (POC, the
highest-volume price level), (3) price then sweeps beyond the range
("manipulation" -- a liquidity grab), (4) a valid reversal signal fires
only when price reverses and closes back through the POC with a
strong-bodied candle (filtering fakeouts via minimum breakout distance in
ATR units AND minimum candle body size in ATR units AND close-near-extreme
strength). This is a genuinely new combination in this repo -- prior
Value-Area/POC entries (2026-09-04-150, 2026-09-08-129, 2026-09-10-001,
2026-09-16-183, 2026-09-18-063/064) all used a RANGE boundary (VAL/VAH) as
the trigger level, never the tight-consolidation-range's own POC combined
with an explicit liquidity-sweep-then-strong-reversal-through-POC
confirmation; and prior liquidity-sweep entries (2026-09-09-087/089,
2026-09-23-046/047, this trigger's iteration 4) used a plain N-bar
swing-low/high as the swept level, never a volume-profile POC.

Signal logic (long side only, daily-bar adaptation)
----------------------------------------------------
- Accumulation range: over the trailing `accum_length` bars, the range
  (high-low)/close must be <= `accum_range_max_pct` (a tight consolidation
  qualifies).
- POC: within that accumulation window, build a coarse volume-weighted
  histogram (weighting each bar's HLC3 by volume) and take the highest-
  volume bin's price as the POC.
- Manipulation: within `max_search_window` bars after the accumulation
  window closes, price must trade below the accumulation range's own low
  (a sweep of the low, i.e. a stop-hunt below support).
- Breakout confirmation (long): on a subsequent bar (still within the
  search window), close crosses back above the POC, the breakout candle's
  body (|close-open|) is at least `min_break_body_atr_mult` * ATR, the
  close-to-POC distance is at least `min_poc_break_atr_mult` * ATR, AND
  the close sits in the upper `close_strength_pct` fraction of that bar's
  own high-low range (strong close, not a weak reversal).
- Exit: max_hold_days time-stop, or close falling back below the POC
  (invalidation).
- Optional close>SMA(trend_window) uptrend gate (default True).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
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
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _poc_price(df_window: pd.DataFrame, n_bins: int = 10) -> float:
    """Coarse volume-weighted POC: highest-volume price bin's midpoint."""
    hlc3 = (df_window["high"] + df_window["low"] + df_window["close"]) / 3.0
    vol = df_window["volume"] if "volume" in df_window.columns else pd.Series(1.0, index=df_window.index)
    lo, hi = hlc3.min(), hlc3.max()
    if hi <= lo:
        return float(hlc3.iloc[-1])
    bins = np.linspace(lo, hi, n_bins + 1)
    bin_idx = np.clip(np.digitize(hlc3.values, bins) - 1, 0, n_bins - 1)
    bin_vol = np.zeros(n_bins)
    for idx, v in zip(bin_idx, vol.values):
        bin_vol[idx] += v
    best_bin = int(np.argmax(bin_vol))
    return float((bins[best_bin] + bins[best_bin + 1]) / 2.0)


def generate_signals(
    price_df: pd.DataFrame,
    accum_length: int = 10,
    accum_range_max_pct: float = 0.06,
    max_search_window: int = 10,
    min_poc_break_atr_mult: float = 0.3,
    min_break_body_atr_mult: float = 0.5,
    close_strength_pct: float = 0.7,
    max_hold_days: int = 10,
    atr_window: int = 14,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)
    atr = _atr(df, atr_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    poc_level = None

    i = accum_length
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = poc_level is not None and close.iloc[i] < poc_level
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # Check accumulation range ending just before bar i (no look-ahead).
        window = df.iloc[i - accum_length:i]
        range_pct = (window["high"].max() - window["low"].min()) / close.iloc[i - 1] if close.iloc[i - 1] else np.inf
        if range_pct <= accum_range_max_pct and bool(uptrend.iloc[i]):
            accum_low = window["low"].min()
            poc = _poc_price(window)

            # Look forward within max_search_window bars for manipulation (sweep below accum_low)
            # followed by a strong close back above POC.
            swept = False
            found_entry = None
            for j in range(i, min(i + max_search_window, n)):
                if not swept and low.iloc[j] < accum_low:
                    swept = True
                    continue
                if swept:
                    body = abs(close.iloc[j] - df["open"].iloc[j])
                    bar_range = high.iloc[j] - low.iloc[j]
                    close_strength = (close.iloc[j] - low.iloc[j]) / bar_range if bar_range > 0 else 0.0
                    a = atr.iloc[j]
                    if pd.isna(a) or a == 0:
                        continue
                    if (
                        close.iloc[j] > poc
                        and (close.iloc[j] - poc) >= min_poc_break_atr_mult * a
                        and body >= min_break_body_atr_mult * a
                        and close_strength >= close_strength_pct
                    ):
                        found_entry = j
                        break

            if found_entry is not None:
                in_position = True
                entry_idx = found_entry
                poc_level = poc
                i = found_entry
                position.iloc[i] = 1
                i += 1
                continue

        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
