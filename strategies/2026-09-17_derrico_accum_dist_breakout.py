"""Strategy: D'Errico Accumulation/Distribution Range Breakout (TASC Aug 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-152):
Domenico D'Errico's TASC Aug 2018 article "Portfolio Strategy Based On
Accumulation/Distribution" (Dow theory framing) detects price CONSOLIDATION
via range contraction: a rolling `Length`-bar high-low range that has
shrunk to less than `ConsolidationFactor` (default 0.75) of the range
measured `Length` bars earlier flags a consolidation zone, whose Top/Bot
are the rolling high/low over that window. Source's own disclosed
TradeStation strategy trades a BREAKOUT from that zone with two extra
confirmations:
    (1) Bot > Bot[Length*3] -- the current consolidation's LOW is HIGHER
        than the low from 3 consolidation-widths earlier, i.e. the
        support floor has been rising across successive consolidations
        (an "accumulation" pattern per Dow theory -- each pullback holds
        a higher floor, not just any sideways range).
    (2) volume `VolDelay` bars ago (averaged over VolAvg bars) exceeds
        `VolRatio` times volume from further back -- a lagged volume
        pickup precedes the breakout, source's own smart-money-footprint
        signal.
Entry: close breaks above Top with both confirmations. Exit: close breaks
back below Bot (source's own simple exit, no time-stop in the original).

This is a genuinely distinct consolidation-breakout mechanic for this repo:
unlike the Rectangle pattern (2026-09-08-111, simple tight-range breakout
with a midpoint stop) or Wyckoff Spring (2026-09-06-123, failed-breakdown-
then-reclaim), D'Errico's construction requires a MULTI-CONSOLIDATION
RISING-FLOOR pattern (Bot > Bot[Length*3]) as its core "accumulation"
signal, not just a single tight range -- explicitly Dow-theory-style
successive-higher-lows-across-consolidations, plus a lagged (not
same-bar) volume confirmation.

Our own addition (flagged as such): a max_hold_days time-stop backstop is
added on top of source's own Bot-breakdown exit, since the source's raw
exit can leave positions open indefinitely if Bot keeps rising with price.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/08/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    length: int = 4,
    consolidation_factor: float = 0.75,
    vol_ratio: float = 1.0,
    vol_avg: int = 4,
    vol_delay: int = 4,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    rng = high.rolling(length).max() - low.rolling(length).min()
    rng_prior = rng.shift(length)

    consolidation = rng < (consolidation_factor * rng_prior)
    top = high.rolling(length).max()
    bot = low.rolling(length).min()

    bot_prior = bot.shift(length * 3)
    rising_floor = bot > bot_prior

    vol_avg_series = volume.rolling(vol_avg).mean()
    vol_delayed = vol_avg_series.shift(vol_delay)
    vol_further_back = vol_avg_series.shift(vol_avg + vol_delay)
    volume_confirm = vol_delayed > (vol_ratio * vol_further_back)

    breakout = close > top.shift(1)  # breakout above the *established* top

    entry = (
        consolidation.shift(1).fillna(False)
        & breakout.fillna(False)
        & rising_floor.fillna(False)
        & volume_confirm.fillna(False)
    )

    exit_breakdown = close < bot

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_breakdown.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
