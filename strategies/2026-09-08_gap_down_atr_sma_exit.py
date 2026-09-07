"""Strategy: Gap-Down Long (low-volume gap + ATR-drop entry + SMA/target/time exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-120):
Per https://www.quantifiedstrategies.com/gap-down-strategy-in-stocks-going-long/,
a gap down (today's high < yesterday's low) accompanied by BELOW-AVERAGE
volume (today's volume < 50-day average volume -- the source's key filter:
"a higher volume most probably means bad news and will likely lead to more
selloff") identifies a controlled, non-panic selloff worth fading. Rather
than buying immediately (source states "this strategy has no edge over the
first 1-4 trading days"), entry is delayed to the NEXT trading day and only
triggered if price falls an additional 0.5x ATR(50) from that day's open
(a further capitulation confirmation). Exit on close crossing above the
10-day SMA, a +7.5% target gain from entry, or a 15-trading-day time-stop.
This is a genuinely different mechanic from the already-tested/rejected
gap-fade variants in this repo (2026-09-03-010: naive open-to-close
same-day academic fade; 2026-09-08-016: intraday single-day IBS-gated
partial-gap-fill target) -- this one is MULTI-DAY (holds via SMA/target/
time-stop, not a same-day close-out), uses a VOLUME filter (not IBS), and
delays entry by a day with an ATR-based capitulation confirmation trigger.

Signal logic
------------
- Gap down day: today's high < yesterday's low.
- Volume filter: today's volume < 50-day average volume (trailing, prior to
  today) -- a controlled selloff, not a volume-driven panic.
- Entry trigger day (the NEXT trading day after a qualifying gap-down day):
  if that day's low falls to or below (that day's open - 0.5 * ATR(50)),
  enter long (using that trigger price as a fill proxy since we only have
  daily OHLC, not intraday ticks).
- Exit: close crosses above the 10-day SMA, OR unrealized gain from entry
  reaches +7.5%, OR max_hold_days (15) trading days elapse -- whichever
  comes first.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 50,
    vol_window: int = 50,
    entry_atr_mult: float = 0.5,
    sma_exit_window: int = 10,
    target_gain: float = 0.075,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low, open_, volume = (
        df["close"], df["high"], df["low"], df["open"], df["volume"],
    )

    atr = _atr(df, atr_window)
    avg_vol = volume.rolling(vol_window).mean().shift(1)

    gap_down = high < low.shift(1)
    controlled_selloff = gap_down & (volume < avg_vol)
    # Qualifying day was YESTERDAY relative to today's potential trigger.
    qualifies_prior_day = controlled_selloff.shift(1).fillna(False)

    entry_trigger_price = open_ - entry_atr_mult * atr
    entry_signal = qualifies_prior_day & (low <= entry_trigger_price)

    sma = close.rolling(sma_exit_window).mean()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            gain = (close.iloc[i] / entry_price) - 1.0 if entry_price else 0.0
            hit_sma_exit = close.iloc[i] > sma.iloc[i] if pd.notna(sma.iloc[i]) else False
            hit_target = gain >= target_gain
            if hit_sma_exit or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = min(entry_trigger_price.iloc[i], open_.iloc[i])
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
