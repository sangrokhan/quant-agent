"""Strategy: RSI With Trend (Kevin Luo, "The RSI & Price Trends", TASC June
2015), read this iteration via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/06/TradersTips.html
(exact TradeStation EasyLanguage strategy code disclosed directly in the
Traders' Tips section, after web_search DDGS backend errored on prior
queries this run -- direct traders.com archive URL navigation to a
previously-unvisited month, discovered by walking forward from adjacent
known TASC months already in this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Luo's own trend detector defines a trend as a persistent swing-high/
swing-low structure where a NEW higher swing high (in an uptrend) or a
new lower swing low (in a downtrend) doesn't just barely eclipse the last
extreme -- it must represent a retrace_pct% MOVE AWAY from the current
swing reference price to count as confirming the trend continuing (once
established, subsequent swings only need to exceed the prior extreme, no
retrace_pct required again). RSI oversold (<30) crossunder entries are
gated to only fire when this trend detector currently reads "up"
(TLDir==1); exit on RSI crossing overbought (>70) OR the trend detector
flipping to "down" (TLDir==-1). This combines a well-tested RSI oversold
entry with a NOVEL swing-retracement trend filter distinct from every
other trend gate in this repo (SMA/EMA-based, ADX-based, Hurst-based, etc.)
because it's a discrete state machine keyed on confirmed ZigZag-style
swing pivots with an asymmetric "first move needs retrace_pct% authority,
subsequent moves just need a new extreme" confirmation rule -- not a
continuous indicator threshold. First Kevin Luo swing-trend-filtered RSI
strategy in this repo.

Exact rule set (translated from TASC Jun 2015 TradeStation EasyLanguage
strategy code, as read this iteration):
    SwingHigh/SwingLow detection: a confirmed 2-bar-strength swing pivot
        (source uses TradeStation's built-in SwingHigh(1, Price, 1, 2) /
        SwingLow(1, Price, 1, 2), i.e. 1 bar of left/right strength with a
        2-bar lookback cap -- approximated here as a local extremum over a
        [-swing_strength, +swing_strength] window).
    Trend state machine (TLDir, persistent across bars):
        On a new confirmed swing high (NewSwingPrice):
          if TLDir<=0 and NewSwingPrice >= SwingPrice*(1+retrace_pct/100):
              TLDir=1 (uptrend confirmed via genuine retrace-authority move)
          elif TLDir==1 and NewSwingPrice >= SwingPrice:
              TLDir stays 1 (a fresh higher high just needs to exceed, no
              retrace_pct required once already in an uptrend)
          SwingPrice updates to NewSwingPrice in either case.
        Mirror-image logic for a new confirmed swing low flipping/
        continuing TLDir=-1.
    RSI(rsi_length) computed on Close.
    Long entry: RSI crosses under `oversold` AND TLDir==1 (trend filter).
    Long exit: RSI crosses over `overbought`, OR (if exit_on_trend_change)
        TLDir flips to -1.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _swing_points(close: np.ndarray, strength: int, n: int):
    """Return (is_swing_high, is_swing_low) boolean arrays: a confirmed
    local extremum with `strength` bars of confirmation on each side."""
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for i in range(strength, n - strength):
        window = close[i - strength : i + strength + 1]
        if close[i] == window.max() and (window == close[i]).sum() == 1:
            is_high[i] = True
        if close[i] == window.min() and (window == close[i]).sum() == 1:
            is_low[i] = True
    return is_high, is_low


def generate_signals(
    price_df: pd.DataFrame,
    rsi_length: int = 14,
    overbought: float = 70.0,
    oversold: float = 30.0,
    retrace_pct: float = 20.0,
    swing_strength: int = 1,
    exit_on_trend_change: bool = True,
    use_trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the RSI-With-Trend rule."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    rsi = _rsi(close, rsi_length)
    close_vals = close.values

    is_high, is_low = _swing_points(close_vals, swing_strength, n)

    retrace_up = 1.0 + retrace_pct / 100.0
    retrace_dn = 1.0 - retrace_pct / 100.0

    tl_dir = np.zeros(n, dtype=int)
    swing_price = close_vals[0] if n > 0 else 0.0
    state = 0
    for i in range(n):
        if is_high[i]:
            new_swing = close_vals[i]
            if state <= 0 and new_swing >= swing_price * retrace_up:
                state = 1
                swing_price = new_swing
            elif state == 1 and new_swing >= swing_price:
                swing_price = new_swing
        elif is_low[i]:
            new_swing = close_vals[i]
            if state >= 0 and new_swing <= swing_price * retrace_dn:
                state = -1
                swing_price = new_swing
            elif state == -1 and new_swing <= swing_price:
                swing_price = new_swing
        tl_dir[i] = state

    rsi_prev = rsi.shift(1)
    cross_under_oversold = (rsi < oversold) & (rsi_prev >= oversold)
    cross_over_overbought = (rsi > overbought) & (rsi_prev <= overbought)

    trend_ok = (tl_dir == 1) if use_trend_filter else np.ones(n, dtype=bool)

    position = np.zeros(n, dtype=int)
    in_long = False
    cu_vals = cross_under_oversold.values
    co_vals = cross_over_overbought.values

    for i in range(n):
        if not in_long:
            if cu_vals[i] and trend_ok[i]:
                in_long = True
        else:
            if co_vals[i]:
                in_long = False
            elif exit_on_trend_change and tl_dir[i] == -1:
                in_long = False
        position[i] = 1 if in_long else 0

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
