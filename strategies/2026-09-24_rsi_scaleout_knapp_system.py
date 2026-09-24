"""Strategy: RSI(14) scale-out long system (Volker Knapp / Active Trader Feb 2010,
via Thomas Bulkowski's writeup).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-131):
Per https://thepatternsite.com/MechanicalRSI.html (Bulkowski, browser_exec),
Active Trader magazine (Feb 2010, "RSI scale-out system" by Volker Knapp)
disclosed exact mechanical rules:
  - Long side only.
  - Buy (tomorrow's open) when 14-period RSI drops below 30.
  - Exit 25% of the position (at tomorrow's open) each time RSI rises through
    45, 60, 75, 90 (four equal 25% scale-out tranches).
  - Stop the ENTIRE remaining position if price falls 5x the 20-day ATR
    below the entry price.
  - Sell the entire remaining position if held 300 days with no scale-out
    exit activity.
Their own 17-stock, 1999-2009 test: 444 trades, +75.9% net, 21% max
drawdown, 70% win rate. Source's own critique/caveat (used here as-is,
without modification, since the repo's job is to test the DISCLOSED rule
faithfully first): RSI rarely reaches 90 in practice, so most exits are the
lower/time-based tranches.

Adaptation for this repo's single-instrument continuous-position contract:
rather than a literal discrete lot-scale-out (which needs share-count
bookkeeping outside this file's scope), this is implemented as a CONTINUOUS
EXPOSURE series (0.0-1.0): entry sets exposure=1.0; each RSI scale-out
threshold crossed reduces remaining exposure by 0.25 (multiplicatively
against whatever fraction remains); the ATR stop and 300-day time-stop force
exposure to 0.0 immediately. This exactly reproduces the source's own
tranche economics for a single continuously-sized position (rather than a
literal N-share portfolio), while remaining testable via
generate_returns()'s pd.Series return contract.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0.0-1.0 continuous exposure)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    entry_rsi_threshold: float = 30.0,
    scaleout_levels=(45.0, 60.0, 75.0, 90.0),
    scaleout_fraction: float = 0.25,
    atr_window: int = 20,
    atr_stop_mult: float = 5.0,
    max_hold_days: int = 300,
) -> pd.Series:
    """Return a continuous [0,1] exposure series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rsi = _rsi(close, rsi_window)
    atr = _atr(df, atr_window)

    close_vals = close.values
    rsi_vals = rsi.values
    atr_vals = atr.values

    exposure = pd.Series(0.0, index=close.index, dtype=float)

    in_position = False
    entry_idx = -1
    entry_price = None
    remaining = 0.0
    levels_hit = [False] * len(scaleout_levels)

    for i in range(n):
        if not in_position:
            # Entry trigger: RSI below entry threshold today -> enter next bar (i+1)
            if not math.isnan(rsi_vals[i]) and rsi_vals[i] < entry_rsi_threshold:
                in_position = True
                entry_idx = i
                entry_price = close_vals[i]
                remaining = 1.0
                levels_hit = [False] * len(scaleout_levels)
        else:
            held_days = i - entry_idx
            atr_i = atr_vals[i]
            stop_hit = (
                entry_price is not None
                and not math.isnan(atr_i)
                and close_vals[i] < entry_price - atr_stop_mult * atr_i
            )
            time_stop_hit = held_days >= max_hold_days

            if stop_hit or time_stop_hit:
                remaining = 0.0
                in_position = False
            else:
                for lvl_i, lvl in enumerate(scaleout_levels):
                    if not levels_hit[lvl_i] and not math.isnan(rsi_vals[i]) and rsi_vals[i] >= lvl:
                        levels_hit[lvl_i] = True
                        remaining = max(0.0, remaining - scaleout_fraction)
                if remaining <= 0.0:
                    in_position = False

        exposure.iloc[i] = remaining if in_position else 0.0

    return exposure.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    entry_rsi_threshold: float = 30.0,
    scaleout_levels=(45.0, 60.0, 75.0, 90.0),
    scaleout_fraction: float = 0.25,
    atr_window: int = 20,
    atr_stop_mult: float = 5.0,
    max_hold_days: int = 300,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    exposure = generate_signals(
        price_df,
        rsi_window=rsi_window,
        entry_rsi_threshold=entry_rsi_threshold,
        scaleout_levels=scaleout_levels,
        scaleout_fraction=scaleout_fraction,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = exposure.shift(1).fillna(0.0) * daily_returns
    return strat_returns
