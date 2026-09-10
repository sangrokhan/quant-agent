"""Strategy: Qullamaggie Episodic Pivot (EP) gap breakout with EMA trail exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per Kristjan Qullamaggie's Episodic Pivot (EP) setup (per Google AI-overview
synthesis of qullamaggie.com and SnapPChart SERP snippets): an EP is a gap
of roughly 10%+ caused by a genuine catalyst (earnings surprise, guidance
change, major news), typically on a stock that had NOT already rallied
significantly beforehand (i.e. not chasing an already-extended trend).
Source's own disclosed volume-confirmation and exit rule: "Breakout: an
earnings surprise on a stock which has not rallied significantly will lead
to a breakout the next day... sell 1/3 to 1/2 of the position after 3-5
days, then trail the rest with the 10- or 21-day EMA." This implementation
operationalizes it as: (1) not-already-extended filter (close within
pre_gap_extension_lookback days was NOT already > pre_gap_extension_pct
above its SMA(pre_gap_sma_window), i.e. hasn't already run up hard), (2) a
gap-up day of gap_pct_threshold or more with volume >= vol_mult x its own
trailing average (genuine catalyst confirmation), (3) long entry the day
after the gap confirms, (4) exit when close crosses below its own
ema_trail_span-period EMA (source's stated trailing mechanism) or a
max_hold_days time-stop backstop. This repo's {0,1} position contract
can't express Qullamaggie's own partial-scale-out sizing, so the full
position is held until the EMA-trail exit rather than partially scaling
out at day 3-5 -- a documented simplification. First large-single-day-gap
"episodic" catalyst-breakout strategy in this repo -- distinct from all
prior small-gap (weekday-gap-continuation, gap-down-fade) and multi-gap
(Bullish Island Reversal) strategies since EP requires BOTH a large
single-day gap threshold AND a not-already-extended pre-condition.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Both accept keyword-arg tunable parameters per RESEARCH_LOOP.md Step 5.
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
    gap_pct_threshold: float = 0.08,
    vol_mult: float = 1.5,
    vol_window: int = 20,
    pre_gap_sma_window: int = 20,
    pre_gap_extension_pct: float = 0.10,
    ema_trail_span: int = 21,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"]

    avg_volume = volume.rolling(vol_window).mean()
    gap_pct = (open_ - close.shift(1)) / close.shift(1)

    sma_pre = close.rolling(pre_gap_sma_window).mean()
    # "not already rallied significantly": yesterday's close was NOT already
    # extended more than pre_gap_extension_pct above its own recent SMA.
    not_extended = (
        (close.shift(1) - sma_pre.shift(1)) / sma_pre.shift(1) < pre_gap_extension_pct
    ).fillna(False)

    gap_up = (gap_pct >= gap_pct_threshold).fillna(False)
    vol_confirmed = (volume >= vol_mult * avg_volume).fillna(False)

    ep_trigger_day = gap_up & vol_confirmed & not_extended
    # Entry the day AFTER the confirmed EP trigger day (avoid look-ahead:
    # generate_returns applies its own additional shift(1) on top of this).
    entry_signal = ep_trigger_day.shift(1).fillna(False)

    ema_trail = close.ewm(span=ema_trail_span, adjust=False).mean()
    exit_trail = (close < ema_trail).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trail.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
