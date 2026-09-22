"""Strategy: Ichimoku Kumo breakout entry + Chikou confirmation, Kijun-sen TRAILING stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://www.dojidojo.org/ichimoku-cloud-breakout-strategy (accessed
2026-09-22). The article gives a specific 3-step entry rule (trend filter via
price vs Kumo, Kumo breakout close, Chikou Span confirmation) AND a specific
exit mechanic that is NOT a binary "close back inside cloud" exit: a
**trailing stop that follows the Kijun-sen (26-period base line) as it moves
each new bar**, i.e. exit as soon as a candle's close crosses below (long) /
above (short) the *current* Kijun-sen value, not a fixed level set at entry.

This is distinct from prior KB Ichimoku entries:
  - 2026-09-05-049 (rejected): binary long/exit-on-reentry-to-cloud, no TK
    cross, no Chikou confirmation, no Kijun trailing stop.
  - 2026-09-05-085 (accepted): TK-cross + above-cloud + Chikou confluence
    entry, but exit mechanic was different (not a Kijun-sen trailing stop).
The differentiator being tested here is specifically the **exit mechanic**:
does a dynamically-trailing Kijun-sen stop (which tightens/loosens with the
26-period midpoint each day) produce a materially different risk/return
profile than the previously-tested static or cloud-based exits, on top of
the same well-documented entry filter (trend + breakout + Chikou
confirmation)?

Signal logic
------------
- Tenkan-sen = (highest high + lowest low) / 2 over `tenkan_window` bars.
- Kijun-sen  = (highest high + lowest low) / 2 over `kijun_window` bars.
- Senkou Span A = (Tenkan + Kijun) / 2, shifted forward `senkou_shift` bars.
- Senkou Span B = (highest high + lowest low) / 2 over `senkou_b_window`
  bars, shifted forward `senkou_shift` bars.
- Kumo (cloud) = the space between Span A and Span B (using their *current*
  bar values, i.e. the cloud as it appears under today's candle, computed
  `senkou_shift` bars ago -- the standard "cloud under price" alignment).
- Chikou Span = close shifted BACK `chikou_shift` bars (lagging line);
  confirmation = today's close > close `chikou_shift` bars ago (bullish) or
  < (bearish) -- a simplified proxy for "Chikou is above/below the price
  from chikou_shift bars ago", consistent with the source's description.
- Entry (long): close > upper Kumo boundary (max(Span A, Span B) at this
  bar) AND close was already trending above the Kumo the previous bar too
  (avoid the very first ambiguous straddle bar) AND Chikou confirmation is
  bullish.
- Exit (long): close < Kijun-sen (the CURRENT day's Kijun-sen value, which
  moves every bar -- the trailing-stop mechanic under test) OR close drops
  back below the lower Kumo boundary (safety net if Kijun exit is too loose
  in a violent reversal).
- Long-only (no shorts) for interface simplicity, matching most other
  single-asset-class strategies in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _donchian_mid(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    return (high.rolling(window).max() + low.rolling(window).min()) / 2.0


def generate_signals(
    price_df: pd.DataFrame,
    tenkan_window: int = 9,
    kijun_window: int = 26,
    senkou_b_window: int = 52,
    senkou_shift: int = 26,
    chikou_shift: int = 26,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    tenkan = _donchian_mid(high, low, tenkan_window)
    kijun = _donchian_mid(high, low, kijun_window)

    span_a_raw = (tenkan + kijun) / 2.0
    span_b_raw = _donchian_mid(high, low, senkou_b_window)

    # Shift forward by senkou_shift, then shift back to align the cloud
    # that is "under" today's candle (standard charting convention: the
    # cloud plotted at bar t was computed senkou_shift bars earlier).
    span_a_aligned = span_a_raw.shift(senkou_shift)
    span_b_aligned = span_b_raw.shift(senkou_shift)

    kumo_upper = pd.concat([span_a_aligned, span_b_aligned], axis=1).max(axis=1)
    kumo_lower = pd.concat([span_a_aligned, span_b_aligned], axis=1).min(axis=1)

    chikou_confirm_bull = close > close.shift(chikou_shift)

    above_cloud = close > kumo_upper
    above_cloud_prev = above_cloud.shift(1).fillna(False)

    entry = above_cloud & above_cloud_prev & chikou_confirm_bull

    exit_kijun = close < kijun
    exit_cloud_fail = close < kumo_lower
    exit_signal = exit_kijun | exit_cloud_fail

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    for i in range(len(close)):
        if not in_pos:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
                in_pos = True
        else:
            if bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    tenkan_window: int = 9,
    kijun_window: int = 26,
    senkou_b_window: int = 52,
    senkou_shift: int = 26,
    chikou_shift: int = 26,
) -> pd.Series:
    """Return daily strategy returns (no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        tenkan_window=tenkan_window,
        kijun_window=kijun_window,
        senkou_b_window=senkou_b_window,
        senkou_shift=senkou_shift,
        chikou_shift=chikou_shift,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Position at t applies to the return realized over t -> t+1: shift
    # position forward by 1 to avoid lookahead bias.
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
