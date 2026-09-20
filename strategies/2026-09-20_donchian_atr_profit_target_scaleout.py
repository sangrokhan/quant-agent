"""Strategy: Donchian Breakout + ATR-N Scaled Profit Targets + Chandelier Trail.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-129):
Per danieltuckerrust's "Seykota Alt 10: Profit Targets" Pine Script
(https://raw.githubusercontent.com/trustdan/trend-following-backtesting-strategies/main/pine-scripts/14_PF-1.232_SPY_seykota_alt10_profit_targets.pine,
visited via browser_exec this iteration), a classic Donchian-breakout
trend-following entry (Turtle-style, already covered in this repo's
plain/pyramided forms -- ids 2026-09-04-054, 2026-09-06-125, 2026-09-07-014,
2026-09-16-174/177) can be improved by NOT holding the full position to a
single trailing-stop exit. Instead, scale OUT of the position at fixed
ATR-multiple ("N") profit milestones (+3N, +6N, +9N from entry) -- "take
money off the table" progressively -- while trailing the LAST remaining
fraction with a Chandelier stop, so a big trend still lets the final piece
run. This differs from every prior Donchian/Turtle entry in this repo
(2026-09-16-174/177's pyramid ADDS units on favorable moves but always
exits the whole position on one trailing-stop trigger; none of them ever
partially closes/de-risks on the way up).

Adaptation note: the source uses discrete unit pyramiding (strategy.entry
calls building up to maxUnits positions) which this repo's single
continuous-position-series generate_signals/generate_returns contract
cannot represent directly. This adaptation instead uses a CONTINUOUS
fractional exposure series that starts at 1.0 on entry and steps DOWN by
1/num_scale_outs at each of the N profit-target milestones (mirroring the
source's "close 1 of maxUnits units per target" mechanic), with the final
remaining fraction trailed by the same Chandelier-stop logic as the source.
Position sizing (add-on pyramiding on favorable moves) is NOT included here
-- this isolates the scale-out-at-targets exit mechanic specifically,
since that novel mechanic (not position-building) is the source's stated
distinguishing idea ("ALTERNATIVE 10: Profit Targets + Trailing Stop").

Signal logic
------------
- Entry: close > rolling(entry_window)-day high of the prior bar (Donchian
  breakout, using yesterday's high so the breakout day itself qualifies).
- N = ATR(atr_window) at the entry bar (fixed for the life of the trade,
  matching the source's `N_entry`).
- Initial stop: entry_price - stop_n_mult * N. If hit before ANY profit
  target, exit fully (full stop-out).
- Profit targets: at entry_price + target1_n*N, target2_n*N, target3_n*N,
  exposure steps down from 1.0 -> 2/3 -> 1/3 -> 0 (the last step, at
  target3_n, is itself governed by a Chandelier trail rather than a fixed
  exit -- if price never reaches target3_n, the surviving fraction still
  trails and can exit earlier via the Chandelier stop).
- Chandelier trail (active once in position, tightens after each target
  hit exactly as in source): trail_stop = rolling_max(high, trail_window)
  since entry - trail_n_mult * N. Exit remaining exposure if close < trail_stop.
- max_hold_days backstop to avoid indefinite holds.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Here generate_signals returns a CONTINUOUS exposure series in
        [0, 1] rather than strictly {0,1}, since the strategy's whole
        point is fractional scale-out; generate_returns applies it the
        same way (shift(1) * daily_ret) as every other strategy file.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 55,
    atr_window: int = 20,
    stop_n_mult: float = 2.0,
    trail_window: int = 22,
    trail_n_mult: float = 3.0,
    target1_n: float = 3.0,
    target2_n: float = 6.0,
    target3_n: float = 9.0,
    max_hold_days: int = 120,
) -> pd.Series:
    """Return a fractional [0,1] long/flat exposure series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    donchian_high = high.rolling(entry_window).max().shift(1)
    atr = _atr(df, atr_window)

    breakout = (close > donchian_high).fillna(False)

    exposure = pd.Series(0.0, index=close.index)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    n_entry = 0.0
    peak_close = 0.0
    targets_hit = 0  # 0, 1, 2, or 3

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            peak_close = max(peak_close, close.iloc[i])
            trail_stop = peak_close - trail_n_mult * n_entry

            # Check profit targets in order (only advance, never regress).
            gain = close.iloc[i] - entry_price
            if targets_hit < 1 and gain >= target1_n * n_entry:
                targets_hit = 1
            if targets_hit < 2 and gain >= target2_n * n_entry:
                targets_hit = 2
            if targets_hit < 3 and gain >= target3_n * n_entry:
                targets_hit = 3

            remaining_frac = max(0.0, 1.0 - targets_hit / 3.0)

            stopped_out = (targets_hit == 0 and close.iloc[i] < (entry_price - stop_n_mult * n_entry))
            trailed_out = (targets_hit > 0 and close.iloc[i] < trail_stop)
            time_out = held >= max_hold_days

            if remaining_frac <= 0.0 or stopped_out or trailed_out or time_out:
                in_position = False
                exposure.iloc[i] = 0.0
                continue
            exposure.iloc[i] = remaining_frac
        else:
            if bool(breakout.iloc[i]) and not pd.isna(atr.iloc[i]) and atr.iloc[i] > 0:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                n_entry = atr.iloc[i]
                peak_close = close.iloc[i]
                targets_hit = 0
                exposure.iloc[i] = 1.0
            else:
                exposure.iloc[i] = 0.0
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (exposure.shift(1).fillna(0) * daily_ret)
    return strategy_ret
