"""Strategy: Exhaustion Gap Reversal (trend-exhaustion gap + volume climax).

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary of "Exhaustion Gap Trading Strategy For
Reversals" (Trading Setups Review, NetPicks cited): unlike a common
continuation gap, an EXHAUSTION gap occurs at the END of a prolonged,
mature trend (source's own rule: an established trend lasting several
weeks to months, here approximated via a `trend_window`-day directional
SMA slope check) and is accompanied by climactic volume (significantly
above its own rolling average, source's own language: "well above the
moving average as late retail buyers or panicked sellers rush in") --
signaling the trend has exhausted itself and a reversal is likely, in
contrast to a mid-trend continuation gap (which this repo's already-
rejected same-day gap-fade strategy, 2026-09-16-079, targeted without any
trend-maturity or volume-climax gating). This implementation is the
DOWNTREND-EXHAUSTION-REVERSAL (long) variant: after a sustained
`trend_window`-day downtrend, a gap-down day with volume >=
`volume_spike_mult` times its own rolling average volume signals capitulation
exhaustion; enter long on the confirming next bar (close above the gap
bar's close), exit when price reverts back above a short-term moving
average or a max_hold_days time-stop -- a genuine multi-day SWING
construction (unlike the same-day intraday-fade mechanic of
2026-09-16-079), testable on daily bars since the "extended trend" and
"climactic volume vs. own rolling average" conditions are both multi-day
constructs already representable in OHLCV data.

Distinct from 2026-09-16-079 (any-size same-day gap fade, no trend-maturity
or volume gating, held only intraday) and from 2026-09-16-085 (selling-
climax single-bar event pattern gated by simple downtrend but using
range/wick shape, not a GAP + trend-maturity-slope + volume-vs-own-average
construction) -- first "exhaustion gap" strategy in this repo (0 prior
matches).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    trend_slope_lookback: int = 20,
    gap_down_threshold: float = 0.01,
    volume_avg_window: int = 20,
    volume_spike_mult: float = 1.75,
    exit_ma_window: int = 15,
    max_hold_days: int = 25,
) -> pd.Series:
    """0/1 long-only position series (downtrend-exhaustion-reversal variant).

    Entry: (1) close has been below its rolling SMA(trend_window) with a
    negative slope over `trend_slope_lookback` bars -- a sustained, mature
    downtrend (source's "extended trend" requirement, approximated via
    SMA-slope rather than an explicit multi-week counter); (2) that bar
    gaps DOWN by more than `gap_down_threshold` (open vs. prior close)
    AND has volume >= `volume_spike_mult` times its own rolling average
    volume -- the "exhaustion gap + climactic volume" signature; (3)
    confirmed by the next bar's close being higher than the gap bar's
    close (entry on that next bar). Exit: close reaches back above the
    `exit_ma_window`-day moving average, or `max_hold_days` bars elapsed.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    sma = close.rolling(trend_window).mean()
    sma_slope = sma.diff(trend_slope_lookback)
    sustained_downtrend = (close < sma) & (sma_slope < 0)

    gap = (open_ - close.shift(1)) / close.shift(1)
    gap_down = gap < -gap_down_threshold

    avg_volume = volume.rolling(volume_avg_window).mean()
    volume_climax = volume >= volume_spike_mult * avg_volume

    exhaustion_bar = (sustained_downtrend & gap_down & volume_climax).fillna(False)

    exhaustion_prev = exhaustion_bar.shift(1).fillna(False)
    confirm = close > close.shift(1)
    entry_trigger = (exhaustion_prev & confirm).to_numpy()

    exit_ma = close.rolling(exit_ma_window).mean()
    exit_trigger = (close >= exit_ma).fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    bars_held = 0
    for i in range(n):
        if in_pos:
            bars_held += 1
            if exit_trigger[i] or bars_held >= max_hold_days:
                in_pos = False
                bars_held = 0
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                bars_held = 0
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    trend_slope_lookback: int = 20,
    gap_down_threshold: float = 0.01,
    volume_avg_window: int = 20,
    volume_spike_mult: float = 1.75,
    exit_ma_window: int = 15,
    max_hold_days: int = 25,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_window=trend_window,
        trend_slope_lookback=trend_slope_lookback,
        gap_down_threshold=gap_down_threshold,
        volume_avg_window=volume_avg_window,
        volume_spike_mult=volume_spike_mult,
        exit_ma_window=exit_ma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
