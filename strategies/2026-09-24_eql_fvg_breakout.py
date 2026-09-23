"""Strategy: Equal-Lows (EQL) liquidity-zone sweep + FVG-confirmed breakout
(long side only), adapted from intraday to daily bars.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per LuxAlgo's "EQH/EQL FVG Breakouts" indicator
(https://www.luxalgo.com/library/indicator/eqh-eql-fvg-breakouts, read this
iteration via browser_exec -- web_search DDGS/Yahoo backend TLS-erroring on
queries attempted this iteration): Equal Lows (EQL) -- two or more pivot
lows within a tight equality threshold of each other, close together in
time -- mark a liquidity pool where stop orders cluster. This repo has 0
prior Equal-Highs/Equal-Lows entries and 6 prior standalone Fair Value Gap
(FVG) entries, but never the COMBINATION the source indicator actually
uses: after price sweeps below an EQL zone (liquidity grab) and then
breaks back UP through it with strong momentum (a candle body >=
min_break_body_atr_mult * ATR) AND that breakout candle leaves behind a
genuine 3-bar Fair Value Gap (low[i] > high[i-2], min_fvg_size_atr_mult *
ATR minimum imbalance size), the setup is considered high-conviction. This
double-confirmation (EQL-sweep-breakout + fresh FVG) is structurally
distinct from every prior standalone FVG entry in this repo (which traded
a retracement INTO an existing gap, never a gap formed BY a liquidity-
sweep breakout) and from every prior liquidity-sweep entry (which never
required a fresh FVG as confirmation).

Signal logic (long side only)
------------------------------
- Pivot lows: rolling `pivot_window`-bar centered fractal lows (confirmed
  with a lag, same pattern as this trigger's MSS Sweeps strategy).
- Equal Lows (EQL): two confirmed pivot lows within `max_eql_distance_bars`
  of each other whose price difference is <= `equality_threshold_pct` of
  price -- together they define an EQL zone at their average price.
- Sweep: a later bar's low dips below the EQL zone price (liquidity grab).
- Breakout + FVG confirmation: within `max_search_window` bars of the
  sweep, a bar closes back above the EQL zone with (a) candle body >=
  min_break_body_atr_mult * ATR, AND (b) that bar or one of the next 2
  bars forms a genuine bullish 3-bar FVG (low[k] > high[k-2]) of size >=
  min_fvg_size_atr_mult * ATR. Entry fires on the bar the FVG confirms.
- Exit: max_hold_days time-stop, or close falling back below the EQL zone
  (invalidation).
- Optional close>SMA(trend_window) uptrend gate (default True).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

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


def _confirmed_pivot_lows(df: pd.DataFrame, pivot_window: int) -> pd.Series:
    low = df["low"]
    window = 2 * pivot_window + 1
    rolling_min = low.rolling(window, center=True).min()
    is_pivot_low_raw = (low == rolling_min)
    return is_pivot_low_raw.shift(pivot_window).fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    max_eql_distance_bars: int = 40,
    equality_threshold_pct: float = 0.015,
    max_search_window: int = 10,
    min_break_body_atr_mult: float = 0.5,
    min_fvg_size_atr_mult: float = 0.1,
    max_hold_days: int = 15,
    atr_window: int = 14,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    is_pivot_low = _confirmed_pivot_lows(df, pivot_window)
    atr = _atr(df, atr_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    pivot_low_indices = [j for j in range(n) if bool(is_pivot_low.iloc[j])]

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    eql_level = None

    i = pivot_window
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = eql_level is not None and close.iloc[i] < eql_level
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # Find an EQL zone from the two most recent confirmed pivot lows
        # available strictly before bar i.
        recent_lows = [j for j in pivot_low_indices if j < i]
        found_zone = None
        if len(recent_lows) >= 2:
            p2 = recent_lows[-1]
            for p1 in reversed(recent_lows[:-1]):
                if p2 - p1 > max_eql_distance_bars:
                    break
                price1, price2 = low.iloc[p1], low.iloc[p2]
                if price2 == 0:
                    continue
                if abs(price1 - price2) / price2 <= equality_threshold_pct:
                    found_zone = (price1 + price2) / 2.0
                    break

        if found_zone is not None and bool(uptrend.iloc[i]) and low.iloc[i] < found_zone:
            # Sweep detected at bar i; search forward for breakout+FVG confirmation.
            confirmed_at = None
            for j in range(i, min(i + max_search_window, n)):
                a = atr.iloc[j]
                if pd.isna(a) or a == 0:
                    continue
                body = abs(close.iloc[j] - open_.iloc[j])
                if close.iloc[j] > found_zone and body >= min_break_body_atr_mult * a:
                    # Check for a fresh bullish FVG at j or the next 2 bars.
                    for k in range(j, min(j + 3, n)):
                        if k < 2:
                            continue
                        gap = low.iloc[k] - high.iloc[k - 2]
                        a_k = atr.iloc[k]
                        if pd.notna(a_k) and a_k > 0 and gap >= min_fvg_size_atr_mult * a_k:
                            confirmed_at = k
                            break
                    if confirmed_at is not None:
                        break
            if confirmed_at is not None:
                in_position = True
                entry_idx = confirmed_at
                eql_level = found_zone
                i = confirmed_at
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
