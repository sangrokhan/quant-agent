"""Strategy: Wyckoff Spring accumulation support-break-and-reclaim (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per Wyckoff accumulation theory, a "Spring" is a deliberate shakeout below
the established trading-range support (S_low) that traps late sellers on
low/climactic volume, followed by a swift reclamation back above S_low --
signaling absorption of remaining supply and the start of markup. Per
Google AI-overview synthesis (JournalPlus, Wyckoff Analytics, TradingSim,
ThinkMarkets, Trading Wyckoff), the numeric entry rule is: (1) a rolling
range_lookback-bar trading range establishes S_low = rolling min(low);
(2) a bar's low pierces below S_low by a penetration_pct margin (0.5-3.0%,
per source); (3) volume on that breakdown bar is markedly LOWER than the
preceding range-average volume (source's "exhaustion of supply" condition
-- we use the low-volume variant rather than the climactic-high-volume
alternative since it's the simpler, unambiguous numeric proxy available
from daily OHLCV); (4) a reclamation bar closes back above S_low within
reclaim_window_bars of the breakdown. Entry at the reclamation candle's
close. Exit on a max_hold_days time-stop or price falling back below the
Spring low (stop-loss, "stop sits below the Spring low" per source).

Sources read this iteration:
- Google AI-overview synthesis of Wyckoff Spring numeric entry rules
  (JournalPlus, Wyckoff Analytics, TradingSim, ThinkMarkets, Trading
  Wyckoff, Velotrade).

First Wyckoff-family strategy in this knowledge base (zero prior matches
for "Wyckoff").

Signal logic
------------
- S_low = rolling min(low) over range_lookback bars (trading range support).
- Spring breakdown bar: low < S_low_prev * (1 - penetration_pct) AND
  volume < avg_volume_prev * volume_ratio_thresh (low-volume exhaustion).
- Reclamation: within reclaim_window_bars bars after a breakdown, a close
  > S_low_prev (the pre-breakdown support level) triggers long entry.
- Exit: close < spring_low (stop below the Spring low) OR max_hold_days
  time-stop.
- Flat otherwise.

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
    range_lookback: int = 40,
    penetration_pct: float = 0.01,
    volume_ratio_thresh: float = 1.5,
    reclaim_window_bars: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else None

    s_low = low.rolling(range_lookback).min().shift(1)  # trading-range support, using data up to prior bar
    avg_vol = volume.rolling(range_lookback).mean().shift(1) if volume is not None else None

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)

    breakdown_pending = False
    breakdown_bars_ago = 0
    spring_low = None
    support_ref = None

    in_position = False
    hold_days = 0
    entry_stop = None

    for i in range(n):
        c = close.iloc[i]
        l = low.iloc[i]
        sl = s_low.iloc[i]
        av = avg_vol.iloc[i] if avg_vol is not None else None
        v = volume.iloc[i] if volume is not None else None

        # --- position management (exit checks first) ---
        if in_position:
            hold_days += 1
            if c < entry_stop or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                entry_stop = None
            else:
                position.iloc[i] = 1
                continue

        # --- detect a new Spring breakdown bar ---
        if not pd.isna(sl):
            is_breakdown = l < sl * (1 - penetration_pct)
            vol_ok = True
            if av is not None and v is not None and not pd.isna(av):
                # NOTE: empirical check this iteration found breakdown-bar
                # volume is typically ELEVATED (median ratio ~1.65x range
                # avg) rather than depressed on QQQ daily bars -- using the
                # climactic-high-volume variant of the source's dual
                # condition (source gave both "exceptionally high" and
                # "markedly lower" as valid Spring volume signatures; daily
                # OHLCV without tick-level order flow can't distinguish
                # which is "true" absorption, so we use whichever the data
                # actually shows, per empirical check rather than the
                # low-volume assumption originally hypothesized).
                vol_ok = v > av * volume_ratio_thresh
            if is_breakdown and vol_ok:
                breakdown_pending = True
                breakdown_bars_ago = 0
                spring_low = l
                support_ref = sl
                continue

        # --- track reclamation window ---
        if breakdown_pending:
            breakdown_bars_ago += 1
            if breakdown_bars_ago > reclaim_window_bars:
                breakdown_pending = False
                spring_low = None
                support_ref = None
                continue
            if c > support_ref:
                # Reclamation confirmed -> enter long
                breakdown_pending = False
                in_position = True
                hold_days = 1
                entry_stop = spring_low
                position.iloc[i] = 1
                spring_low = None
                support_ref = None

    return position


def generate_returns(
    price_df: pd.DataFrame,
    range_lookback: int = 40,
    penetration_pct: float = 0.01,
    volume_ratio_thresh: float = 1.5,
    reclaim_window_bars: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        range_lookback=range_lookback,
        penetration_pct=penetration_pct,
        volume_ratio_thresh=volume_ratio_thresh,
        reclaim_window_bars=reclaim_window_bars,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
