"""Strategy: Gap-Down + Low-IBS + Low-RSI swing mean-reversion with adaptive
close-vs-time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per QuantifiedStrategies.com's gap-trading swing article
(https://www.quantifiedstrategies.com/gap-trading-strategies/, "Gap trading
in swing trading" section, fully disclosed non-paywalled rule): a gap-down
opening combined with weak prior-day IBS and a low prior-day 5-day RSI marks
oversold exhaustion worth a long entry at today's open. The source's own
S&P-500-futures backtest (2011-2021, 5-min data collapsed to a daily-style
swing rule) reports an average gain of 0.48% per trade and profit factor
1.8, and states the SPY EOD version also shows a rising equity curve with
~0.5% average gain per trade. The source explicitly frames this as
capturing "the extra risk premium of the gap down opening" -- an
overnight-risk-premium rationale distinct from the pure overnight-sentiment-
reversal rationale behind this repo's already-rejected 2026-09-03-010.

Source's stated rule (adapted to this repo's EOD-bar interface, since we
only have daily OHLC, not 5-minute intraday data):
  1. Today's open must gap down by at least `gap_down_pct` vs yesterday's
     close (source: >=0.15%).
  2. Yesterday's IBS = (close-low)/(high-low) must be <= `ibs_threshold`
     (source: 0.25).
  3. Yesterday's 5-day RSI (Wilder RSI, period=5, normalized 0-1 by /100)
     must be <= `rsi_threshold` (source: 0.45).
  4. If 1-3 all true: buy at today's open (approximated here by entering
     the position such that today's full-day return, open effectively
     captured via the day's raw close/open return convention used by this
     repo's return-space model -- see note below).
  5. Exit at today's close if today's close > yesterday's close (gap got
     filled/exceeded intraday -- fast exit); otherwise hold overnight,
     checking the same "close > entry-day's prior close" condition each
     subsequent day, up to a `max_hold_days` safety time-stop (source
     doesn't specify a hard cap; we add one per this repo's convention,
     e.g. 2026-09-07-005's use of a fixed multi-day cap for open-ended
     signal exits).

Note on daily-bar approximation: this repo's `generate_returns` framework
uses close-to-close returns exclusively (see reference strategy
2026-09-07_ibs_5day_low_timeexit.py) -- there is no separate open-price
return leg available to other strategies in this repo either, so entering
"at open" is modeled the same way every other strategy here models
same-day entries: the position is set to 1 starting the entry day, and
`position.shift(1) * daily_ret` (close-to-close) is used for VBT-consistent
accounting. This slightly overstates the true open-to-close capture but is
consistent with how every prior gap/candlestick strategy in this repo
already handles entry-day accounting (see e.g. 2026-09-06-153 Gap-and-Go).

Novelty vs prior entries: distinct from 2026-09-03-010 (gap-down fade
without IBS/RSI conditions, same-day open-to-close only, no overnight
hold), 2026-09-06-153 (gap continuation not reversion), and every existing
IBS-family entry (2026-09-04-089/158/159, 2026-09-05-019, 2026-09-07-005 --
none combine a gap-down trigger with IBS AND RSI as a 3-way AND-gate, and
none use the source's adaptive "exit at close if filled, else hold"
mechanic).

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


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)  # neutral when avg_loss is 0 (no losses -> not oversold)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    gap_down_pct: float = 0.15,
    ibs_threshold: float = 0.25,
    rsi_period: int = 5,
    rsi_threshold: float = 45.0,
    max_hold_days: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low, open_ = df["close"], df["high"], df["low"], df["open"]

    day_range = (high - low).replace(0.0, np.nan)
    ibs = ((close - low) / day_range).fillna(0.5)
    rsi = _wilder_rsi(close, rsi_period)

    prev_close = close.shift(1)
    gap_pct = (open_ - prev_close) / prev_close * 100.0

    # Conditions evaluated on YESTERDAY's IBS/RSI (per source's rule) and
    # TODAY's gap (today's open vs yesterday's close).
    ibs_yesterday = ibs.shift(1)
    rsi_yesterday = rsi.shift(1)

    entry = (
        (gap_pct <= -abs(gap_down_pct))
        & (ibs_yesterday <= ibs_threshold)
        & (rsi_yesterday <= rsi_threshold)
    )
    entry = entry.fillna(False)

    n = len(df)
    close_arr = close.to_numpy()
    prev_close_arr = prev_close.to_numpy()
    entry_arr = entry.to_numpy()
    pos_arr = np.zeros(n, dtype=int)

    in_pos = False
    entry_ref_close = np.nan  # yesterday's close at time of entry (fill target)
    hold_counter = 0

    for i in range(n):
        if in_pos:
            hold_counter += 1
            filled = close_arr[i] > entry_ref_close
            if filled or hold_counter >= max_hold_days:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_counter = 0
                entry_ref_close = prev_close_arr[i]
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    gap_down_pct: float = 0.15,
    ibs_threshold: float = 0.25,
    rsi_period: int = 5,
    rsi_threshold: float = 45.0,
    max_hold_days: int = 7,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        gap_down_pct=gap_down_pct,
        ibs_threshold=ibs_threshold,
        rsi_period=rsi_period,
        rsi_threshold=rsi_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
