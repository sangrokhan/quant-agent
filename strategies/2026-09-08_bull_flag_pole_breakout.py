"""Strategy: Bull Flag pattern (flagpole + pullback + breakout continuation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-130):
Per https://www.warriortrading.com/bull-flag-trading/'s disclosed mechanical
rule: a bull flag forms when (1) a "flagpole" -- a strong up-move on
above-average volume -- is followed by (2) a "flag" -- a shallow pullback
of 2-5 candles that does NOT retrace more than 50% of the flagpole move
(a deeper retrace is the source's own stated "warning sign of failure") --
and (3) a breakout: the first candle making a new high above the flag's own
high resumes the uptrend. Stop-loss at the low of the flag/pullback;
source's own stated target is a 2:1 reward:risk ratio.

This is a DISTINCT construction from every other consolidation-breakout
pattern already tested in this repo:
  - Rectangle (2026-09-08-111): a flat, non-trending horizontal range (no
    directional flagpole precondition, no 50%-retracement cap).
  - Rising Three Methods (2026-09-08-110): a rigid 5-CANDLE count (1 big
    up, 3 small down, 1 big up) rather than a variable-length flagpole +
    variable-length (2-5 candle) pullback with an explicit retracement-depth
    filter.
  - Ascending/Falling Wedge/Triangle (2026-09-08-112/113, 2026-09-08-102):
    trendline-convergence constructions, not a discrete flagpole-move
    magnitude + retracement-depth rule.
The flagpole-move-size and 50%-retracement-cap are this pattern's
distinguishing, source-disclosed numeric rules.

Signal logic (daily-bar adaptation of the source's intraday day-trading rule)
------------------------------------------------------------------------------
- Flagpole: a `pole_window`-day (default 3) cumulative return >=
  `pole_min_return` (default 0.05 = 5%) on above-average volume (mean volume
  over the pole window >= `pole_vol_mult` x its own trailing 20-day average)
  marks a valid pole ending at bar t.
- Flag (pullback): over the following `flag_min_days`-`flag_max_days` bars
  (default 2-5), price pulls back but the LOWEST close during the pullback
  stays at/above `retrace_cap` (default 0.50) of the pole's move retraced
  from the pole's high (i.e. does not retrace more than 50%).
- Breakout entry: the first bar within the pullback window whose close
  breaks above the running high of the flag-so-far (the "first candle to
  make a new high" rule) triggers a long entry at that bar's close.
- Exit: stop-loss at the flag's own low (close falling below it), a 2:1
  reward:risk take-profit target (entry + 2x(entry-stop_price)), or a
  `max_hold_days` time-stop backstop, whichever comes first.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    pole_window: int = 3,
    pole_min_return: float = 0.05,
    pole_vol_mult: float = 1.2,
    flag_min_days: int = 2,
    flag_max_days: int = 5,
    retrace_cap: float = 0.50,
    reward_risk: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    n = len(df)

    avg_vol20 = volume.rolling(20).mean()

    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    i = pole_window + 20  # need enough history for avg_vol20 and pole lookback
    while i < n:
        if in_position:
            held = i - entry_idx
            price_now = close.iloc[i]
            if price_now <= stop_price or price_now >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # Check for a valid flagpole ending at bar i (the pole's last bar).
        pole_start = i - pole_window
        pole_return = (close.iloc[i] / close.iloc[pole_start]) - 1.0
        pole_vol_ok = bool(
            avg_vol20.iloc[i] is not None
            and avg_vol20.iloc[pole_start - 1] is not None
            and avg_vol20.iloc[i] >= pole_vol_mult * avg_vol20.iloc[pole_start - 1]
        ) if pole_start - 1 >= 0 else False

        if pole_return >= pole_min_return and pole_vol_ok:
            pole_high = high.iloc[pole_start : i + 1].max()
            pole_low = low.iloc[pole_start : i + 1].min()
            pole_move = pole_high - pole_low
            retrace_floor = pole_high - retrace_cap * pole_move

            # Scan forward up to flag_max_days for a valid pullback + breakout.
            flag_high_so_far = high.iloc[i]  # running high of the flag window
            flag_low_so_far = low.iloc[i]
            breakout_found = False
            for j in range(i + 1, min(i + 1 + flag_max_days, n)):
                days_in_flag = j - i
                # Retracement-depth check: lowest close so far in the flag
                # must not have breached the 50%-retrace floor.
                lowest_close_in_flag = close.iloc[i + 1 : j + 1].min() if j >= i + 1 else close.iloc[i]
                if lowest_close_in_flag < retrace_floor:
                    break  # failed flag (too deep a retrace) -- abandon this pole
                flag_low_so_far = min(flag_low_so_far, low.iloc[j])
                if days_in_flag >= flag_min_days and close.iloc[j] > flag_high_so_far:
                    # Breakout: entry at this bar's close.
                    entry_price = close.iloc[j]
                    stop_price = flag_low_so_far
                    risk = entry_price - stop_price
                    if risk > 0:
                        target_price = entry_price + reward_risk * risk
                        in_position = True
                        entry_idx = j
                        position.iloc[j] = 1
                        breakout_found = True
                        i = j + 1
                    break
                flag_high_so_far = max(flag_high_so_far, high.iloc[j])
            if breakout_found:
                continue
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
