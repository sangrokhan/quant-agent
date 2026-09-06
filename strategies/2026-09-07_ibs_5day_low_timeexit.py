"""Strategy: IBS + 5-Day-Low breakdown mean reversion with fixed time-exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-005):
Per QuantifiedStrategies.com's "5-Day Low of The Range Strategy" (own
disclosed rule, non-paywalled): "simple criteria of IBS lower than 0.25 and
the close lower than the lowest low of the previous 5 days" identifies a
short-term panic/exhaustion setup worth a mean-reversion long. The source's
own backtest (SPY, 1993-2026) reports 309/517 (~60%) winning trades,
"profitability peaks between 3-7 days" with a fixed HOLDING-PERIOD exit
(not a signal-based exit) yielding 10.76% annualized vs buy-and-hold.

This is distinct from every other IBS-family strategy already tested in
this repo (2026-09-04-089 simple IBS threshold cross with SMA-band filter,
2026-09-04-158/159 N-day-averaged IBS with trend gate, 2026-09-05-019
4-condition "Adjusted Failed Bounce" pattern) because:
  1. It combines single-day IBS (not averaged) with a Donchian-style
     "new 5-day low" breakdown confirmation (not IBS alone).
  2. Exit is a pure FIXED time-stop (source's own 3-7 day sweet spot),
     not a signal-based exit (IBS recovery / trend break) as in every
     prior IBS strategy here.
  3. No 200-day trend filter -- source's own backtest is unconditional
     (applies across the full 1993-2026 sample regardless of regime).

Signal logic
------------
- IBS = (close - low) / (high - low), single-day, no averaging.
- 5-day rolling low = min(low) over the trailing `lookback_days` bars,
  EXCLUDING today (i.e. shifted by 1) so "close < lowest low of the
  previous N days" is evaluated causally against strictly prior bars.
- Entry (long): IBS < ibs_threshold AND close < prior N-day low.
- Exit: fixed holding period of `hold_days` trading days (source's own
  3-7 day sweet spot; default 5), no signal-based early exit.
- Flat otherwise. No trend filter (testing the source's claim that this
  works unconditionally, unlike this repo's other IBS variants which
  needed a trend gate to pass).

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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
    ibs_threshold: float = 0.25,
    lookback_days: int = 5,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    day_range = (high - low).replace(0.0, np.nan)
    ibs = ((close - low) / day_range).fillna(0.5)

    # "lowest low of the previous N days" -- strictly prior bars, causal.
    prior_n_low = low.shift(1).rolling(lookback_days).min()

    entry = (ibs < ibs_threshold) & (close < prior_n_low)
    entry = entry.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_counter = 0
    entry_arr = entry.to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_counter += 1
            if hold_counter >= hold_days:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    ibs_threshold: float = 0.25,
    lookback_days: int = 5,
    hold_days: int = 5,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        ibs_threshold=ibs_threshold,
        lookback_days=lookback_days,
        hold_days=hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
