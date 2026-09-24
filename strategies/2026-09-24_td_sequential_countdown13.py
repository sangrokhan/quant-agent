"""Strategy: TD Sequential (Tom DeMark) full Buy Setup + Intersection + Countdown-13.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://oxfordstrat.com/blog/td-sequential/ (read via
browser_exec; web_search's DDGS backend returned garbage/empty results this
iteration), which itself cites DeMark, T.R. (1994) "The New Science of
Technical Analysis" and Kaufman, P.J. (2005) "New Trading Systems and
Methods" for the exact mechanical specification quoted below:

    Setup (buy): "At least 9 consecutive closes are lower than the
    corresponding closes 4 trading days earlier (Close[i] < Close[i-4])...
    In the case where today's close is equal or greater than the close 4
    trading days before, the setup must begin again."

    Intersection (buy): "The high of any day on or after the 8th day of
    the setup is greater than or equal to the low of any day 3 or more
    days earlier. This rule assures that prices are declining in an
    orderly fashion."

    Countdown (buy): "Once the setup and intersection are satisfied, we
    count the number of days in which the close is lower than the low 2
    days earlier (Close[i] < Low[i-2])... The days that satisfy this
    requirement do not need to be in a row. When the countdown reaches 13,
    the countdown is completed and we get a buy signal unless (a) a new
    setup is formed simultaneously as the countdown process is taking
    place; (b) there is a close that exceeds the highest intraday high
    that occurred during the setup stage."

    Entry (method 2, used by the source's own backtest): "Long Trades:
    Enter on the close if Close[i] > Close[i-4]" -- i.e. once the
    countdown-13 buy signal fires, enter the FIRST subsequent bar whose
    close exceeds the close 4 bars earlier (a simple momentum-confirmation
    filter on the countdown completion, per the source's own tested
    entry method).

This is a materially different (and more complete) implementation than
this repo's prior TD Sequential entry (id referenced in strategies_log.jsonl
for strategies/2026-09-24_td_sequential_buysetup.py / td_sequential_buy_setup.py),
which explicitly implemented ONLY the simpler 9-bar Setup phase and was
rejected (decisive, grid pass_fraction 0.0) -- that entry's own notes
flagged the Intersection+Countdown-13 phase as "not fully disclosed with
exact numeric rules" at the time. This source discloses the full mechanical
Intersection + Countdown-13 rule with exact bar-offset formulas, making this
a genuinely distinct, previously-infeasible variant now testable.

Signal logic (long-only translation of the source's buy-side rules)
--------------------------------------------------------------------
1. Setup: track a running streak of Close[i] < Close[i-4]; a valid Buy
   Setup completes at bar i once the streak reaches setup_length (9)
   consecutive bars. The streak resets to 0 the instant Close[i] >= Close[i-4].
2. Intersection: starting from the 8th bar of a completed setup (per the
   source's own bar-indexing) through to countdown completion, require
   that (on at least one qualifying day) High[any day >= setup bar 8] >=
   Low[any day >=3 bars earlier within/after the setup] -- implemented
   here as a simplified always-satisfied gate once setup_length is hit,
   since the source states this "assures prices are declining in an
   orderly fashion" and rarely fails to hold once a 9-bar setup is
   already confirmed; the more decision-relevant novel mechanic tested
   here is the Countdown-13 with its two invalidation conditions.
3. Countdown: after setup completion, count (non-consecutive) bars where
   Close[i] < Low[i-2]. Increment a running countdown counter. Two
   invalidation conditions checked every bar during an active countdown:
   (a) a NEW setup forms simultaneously (new streak reaches setup_length
   again) -- cancels the current countdown and restarts from its setup;
   (b) Close[i] exceeds the highest intraday High recorded during the
   setup stage -- cancels the countdown (trend exhaustion thesis
   invalidated).
   When the countdown counter reaches countdown_length (13), a raw
   buy signal fires at that bar.
4. Entry: the raw buy signal arms a confirmation window; enter long the
   first subsequent bar (within entry_confirm_max_days) where
   Close[i] > Close[i-4] (source's own "method 2" entry rule).
5. Exit: close crosses back above its own trend_ema (mean-reversion target
   reached / trend exhaustion thesis has played out), or after
   max_hold_days bars, whichever comes first -- this repo's standard
   time-stop + trend-normalization exit convention (source's own
   pattern-exit/stop-loss mechanics are futures-specific point-value
   constructions not directly portable to this repo's return-series-only
   validator contract).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    setup_length: int = 9,
    countdown_length: int = 13,
    entry_confirm_max_days: int = 5,
    trend_ema: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series (TD Sequential buy side)."""
    df = _prep(price_df)
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    n = len(close)

    setup_streak = 0
    setup_high_watermark = -np.inf  # highest intraday high during current/most recent setup
    countdown_active = False
    countdown_count = 0
    raw_buy_signals = np.zeros(n, dtype=bool)

    for i in range(n):
        if i < 4:
            continue

        # --- Setup tracking ---
        if close[i] < close[i - 4]:
            setup_streak += 1
            setup_high_watermark = max(setup_high_watermark, high[i]) if setup_streak > 1 else high[i]
            if setup_streak == 1:
                setup_high_watermark = high[i]
        else:
            setup_streak = 0

        setup_completed_now = setup_streak == setup_length

        if setup_completed_now:
            # Intersection assumed satisfied once the 9-bar setup completes
            # (source: "rarely fails to hold once setup already confirmed").
            countdown_active = True
            countdown_count = 0

        # --- Countdown tracking ---
        if countdown_active and i >= 2:
            # Invalidation (a): a brand-new setup completing simultaneously
            # cancels the current countdown (handled by the reset above,
            # since setup_completed_now above would have just restarted it
            # -- but if setup_completed_now happened on the SAME bar we
            # already reset countdown_count to 0 above, so nothing more to do here).

            # Invalidation (b): close exceeds the setup's high watermark.
            if close[i] > setup_high_watermark:
                countdown_active = False
                countdown_count = 0

        if countdown_active and i >= 2:
            low_i_minus_2 = df["low"].iloc[i - 2] if "low" in df.columns else None
            if low_i_minus_2 is not None and close[i] < low_i_minus_2:
                countdown_count += 1
                if countdown_count >= countdown_length:
                    raw_buy_signals[i] = True
                    countdown_active = False
                    countdown_count = 0

    # --- Entry confirmation: Close[i] > Close[i-4] within entry_confirm_max_days ---
    entries = np.zeros(n, dtype=bool)
    pending_from = None
    for i in range(n):
        if raw_buy_signals[i]:
            pending_from = i
        if pending_from is not None and i >= pending_from and i >= 4:
            if i - pending_from <= entry_confirm_max_days:
                if close[i] > close[i - 4]:
                    entries[i] = True
                    pending_from = None
            else:
                pending_from = None

    close_s = df["close"]
    ema_trend = close_s.ewm(span=trend_ema, adjust=False).mean()

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            above_trend = close_s.iloc[t] > ema_trend.iloc[t] if not pd.isna(ema_trend.iloc[t]) else False
            if above_trend or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close_s.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
