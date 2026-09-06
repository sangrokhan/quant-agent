"""Strategy: Rolling-swing-low Anchored VWAP crossover + ATR hard stop-loss.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Direct revisit of the near-miss rolling-swing-low Anchored VWAP crossover
strategy (2026-09-04-138, rejected: Sharpe 0.836 vs 1.0 threshold AND
max_drawdown 0.298 vs 0.25 threshold, both narrowly failing, with clean
TC-survival/walk-forward/param-sensitivity passes on 175 trades -- not a
thin sample). That prior strategy had no stop-loss at all -- it only exited
on an AVWAP cross-back or a 60-day time-stop, so a sharp adverse move after
entry could ride all the way to the time-stop.

Per trader-dale.com's "Master Anchored VWAP: 3 Simple Strategies for
Smarter Trading" (read this iteration -- a source not previously visited in
this repo, distinct from the trendspider.com concept source used for
2026-09-04-138): "Stop Loss Placement: Place your stop loss just beyond the
opposite side of the AVWAP line (or outside the outer standard deviation
band if using AVWAP bands)." This strategy operationalizes that as a hard
ATR-based protective stop set at entry time (entry_price - atr_stop_mult *
ATR(atr_window), i.e. "just beyond" the AVWAP support the trade is
predicated on) and exits immediately if the daily low breaches it -- a
direct, source-grounded fix targeting the exact prior rejection reason
(excess drawdown), without altering the underlying entry logic or the
crossover exit at all, isolating whether a stop-loss alone rescues the
strategy.

Signal logic
------------
- Identical rolling-swing-low Anchored VWAP entry/exit logic to
  2026-09-04-138 (anchor to the most recent rolling `lookback`-day lowest
  low; long entry on close crossing above the anchored VWAP; exit on close
  crossing back below it, or a `max_hold_days` time-stop).
- NEW: on entry, set a hard stop at entry_close - atr_stop_mult * ATR(atr_window)
  (ATR computed as of the entry bar). If any subsequent bar's low trades
  at/below that stop level while still in the position, exit that bar
  (stop-loss triggered) rather than waiting for the AVWAP cross-back or
  time-stop.
- Long-only, flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _anchored_vwap(df: pd.DataFrame, lookback: int) -> pd.Series:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    volume = df["volume"].to_numpy() if "volume" in df.columns else np.ones(len(df))
    typical = (high + low + close) / 3.0
    n = len(df)

    avwap = np.full(n, np.nan)
    anchor_idx = 0
    cum_pv = 0.0
    cum_v = 0.0

    for i in range(n):
        start = max(0, i - lookback + 1)
        window_low = low[start:i + 1]
        local_min_pos = start + int(np.argmin(window_low))

        if local_min_pos != anchor_idx:
            anchor_idx = local_min_pos
            cum_pv = 0.0
            cum_v = 0.0
            for j in range(anchor_idx, i + 1):
                cum_pv += typical[j] * volume[j]
                cum_v += volume[j]
        else:
            cum_pv += typical[i] * volume[i]
            cum_v += volume[i]

        avwap[i] = cum_pv / cum_v if cum_v > 0 else np.nan

    return pd.Series(avwap, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 40,
    max_hold_days: int = 60,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(df)

    avwap = _anchored_vwap(df, lookback)
    atr = _atr(df, atr_window)
    close_prev = close.shift(1)
    avwap_prev = avwap.shift(1)

    entry_trigger = (close > avwap) & (close_prev <= avwap_prev)
    exit_trigger = (close < avwap) & (close_prev >= avwap_prev)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    stop_level = None
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else False
            stopped = stop_level is not None and low.iloc[i] <= stop_level
            if stopped or et or hold_count >= max_hold_days:
                in_pos = False
                stop_level = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                atr_val = atr.iloc[i]
                if pd.notna(atr_val):
                    stop_level = float(close.iloc[i]) - atr_stop_mult * float(atr_val)
                else:
                    stop_level = None
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 40,
    max_hold_days: int = 60,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        lookback=lookback,
        max_hold_days=max_hold_days,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
