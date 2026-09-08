"""Strategy: Bullish Doji Star 3-candle reversal, breakout-above-candle3-high
entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-056):
Per howtotrade.com's Doji Star trading rules (browser_exec fallback --
web_search's DuckDuckGo backend errored with a TLS connection error), the
Bullish Doji Star is a 3-candle reversal in a downtrend: candle1 long
bearish, candle2 a Doji (near-zero body) that gaps down from candle1,
candle3 a long bullish candle. Source's own explicit entry rule: buy order
placed ABOVE candle3's high (a breakout confirmation, not simply candle3's
close) -- distinct from the already-tested Morning Star (2026-09-06-161,
rejected: decisive 0/72 grid pass, only 1 signal over 7.5yr QQQ sample)
which enters at candle3's close crossing above candle1's midpoint, and
distinct from Bullish Abandoned Baby (2026-09-09-037, rejected: 0/192 grid
cells, zero signal generation) which requires TWO non-overlapping gaps.
Doji Star only requires ONE gap (candle1->candle2) and the entry trigger
is a subsequent breakout above candle3's high on a later bar, not
necessarily candle3 itself -- this loosens the pattern vs. Abandoned Baby
while still requiring genuine Doji-candle indecision (unlike Morning Star
which allows any small-bodied candle2). Source's stop-loss rule: below the
Doji's low.

First Bullish Doji Star strategy in this repo.

Signal logic
------------
- Candle1 (2 bars back) bearish: close[-2] < open[-2].
- Candle2 (1 bar back) is a Doji: |close[-1] - open[-1]| <= doji_body_pct
  * (high[-1] - low[-1]), AND gaps down from candle1 (open[-1] <
  close[-2]).
- Candle3 (current bar) bullish: close > open.
- Entry trigger: close (any subsequent bar, checked each bar after the
  3-candle setup forms) breaks above candle3's high (source's explicit
  "buy order placed above the third candle's high" rule) within
  `breakout_lookback` bars of the pattern forming.
- Exit: close falls below the Doji's low (source's stop-loss rule), OR a
  max_hold_days time-stop.

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


def generate_signals(
    price_df: pd.DataFrame,
    doji_body_pct: float = 0.1,
    breakout_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    candle1_bearish = close.shift(2) < open_.shift(2)
    rng2 = (high.shift(1) - low.shift(1)).replace(0, float("nan"))
    candle2_doji = ((close.shift(1) - open_.shift(1)).abs() / rng2) <= doji_body_pct
    candle2_gaps_down = open_.shift(1) < close.shift(2)
    candle3_bullish = close > open_

    pattern_formed = candle1_bearish & candle2_doji & candle2_gaps_down & candle3_bullish
    candle3_high = high.where(pattern_formed)
    doji_low = low.shift(1).where(pattern_formed)

    # Forward-fill the pending pattern's reference levels for up to
    # breakout_lookback bars, waiting for a breakout above candle3's high.
    pending_high = candle3_high.ffill(limit=breakout_lookback)
    pending_low = doji_low.ffill(limit=breakout_lookback)
    bars_since_pattern = pattern_formed[::-1].cumsum()[::-1]  # placeholder, unused

    # Track how many bars since the pattern formed to bound the lookback.
    pattern_idx = pd.Series(range(len(df)), index=df.index).where(pattern_formed).ffill()
    bars_elapsed = pd.Series(range(len(df)), index=df.index) - pattern_idx
    within_lookback = (bars_elapsed >= 0) & (bars_elapsed <= breakout_lookback)

    breakout_signal = (close > pending_high) & within_lookback & pending_high.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    stop_level = None
    for i in range(len(close)):
        if not in_pos:
            bs = breakout_signal.iloc[i]
            if bool(bs) if pd.notna(bs) else False:
                in_pos = True
                entry_idx = i
                stop_level = pending_low.iloc[i]
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            c = close.iloc[i]
            stop_hit = pd.notna(stop_level) and c < stop_level
            if stop_hit or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    doji_body_pct: float = 0.1,
    breakout_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        doji_body_pct=doji_body_pct,
        breakout_lookback=breakout_lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
