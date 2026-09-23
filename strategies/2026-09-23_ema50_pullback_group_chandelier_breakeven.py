"""Strategy: EMA50-trend pullback-group breakout with breakeven-then-chandelier trail.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-... this iter):
Per MGEQuant's Sept 18 2026 dev log entry ("EMA50 Chandelier: what it is for",
https://mgequant.com/DevelopmentLogs/Strategies/2026/09-September.html, read
via browser_exec this iteration -- web_search returned only generic backend
listing pages for this query, so the browser fallback was used to read the
actual devlog content), a public trading-education walkthrough construction:
a 50-period EMA defines trend; after the EMA cross the strategy waits for a
"run of pullback bars" (consecutive bars pulling back against the new trend),
then places a stop-entry beyond the extreme of that pullback group (i.e. a
breakout confirmation that the pullback has ended and trend resumed). Once
filled, a fixed 2R profit target is set, the stop is moved to breakeven at
1R, and a Chandelier trailing stop takes over from there. Rationale (source's
own framing): trading the *resumption* of an established trend after a
disciplined multi-bar pullback, rather than either the raw EMA cross itself
or an undefined single-bar dip, should filter out weak/premature entries
while letting the breakeven-then-trail exit capture extended trend legs.

Distinct from this repo's prior Chandelier-family entries: 2026-09-04-035
(Chandelier used only as a trend regime FILTER, StochRSI dip-buy signal, no
pullback-group breakout entry, no breakeven mechanic); 2026-09-09-064/065
(Chandelier LINE crossing itself is the entry trigger, no discrete pullback-
bar-group stop-entry construction, no breakeven-at-1R rule); 2026-09-04-025
(all-time-high breakout + chandelier exit only, no pullback/breakeven). This
is the first strategy in this repo combining (a) an EMA-trend pullback-group
stop-entry trigger, (b) a breakeven stop move at 1R, and (c) a chandelier
trail taking over afterward.

Daily-bar adaptation notes (source's fleet is documented on 1-minute NQ
futures bars; this repo's data/loaders.py provides only daily OHLCV via
yfinance/ccxt): a "pullback bar" here is any bar whose close moves against
the current EMA-trend direction relative to the prior bar's close (a simple,
mechanically identical daily-bar analog of "a run of bars against trend").
The pullback GROUP is any run of >= pullback_min_bars consecutive such bars;
the stop-entry trigger level is the extreme (low for a long) of that group,
confirmed once price closes back beyond it.

Signal logic
------------
- Trend: close > EMA(ema_period) defines an uptrend (long-only per SAFETY.md).
- Track the current unbroken run of down-closing bars (close < close.shift(1))
  while in an uptrend; once the run reaches pullback_min_bars, the "pullback
  group" low is locked in as that run's minimum low.
- Entry trigger: close breaks back ABOVE the locked pullback-group low PLUS a
  breakout_atr_mult * ATR(atr_period) buffer (stop-entry analog), while still
  in an EMA uptrend.
- Initial stop: the pullback-group's own low. R = entry_price - initial_stop.
- Profit target: entry_price + target_r_mult * R (source's disclosed 2R).
- Breakeven: once unrealized gain >= 1R, the stop is moved up to entry_price
  (breakeven_r_mult, source's disclosed 1R).
- After breakeven triggers, the stop instead trails via a Chandelier Exit
  (chandelier_period, chandelier_mult) computed from the running highest high
  since entry, whichever is higher (never loosens).
- Exit: price closes below the active stop (initial/breakeven/chandelier,
  whichever regime is active), or the profit target is hit, or a
  max_hold_days time-stop backstop (not in the bare source rule, added per
  this repo's convention).

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 50,
    pullback_min_bars: int = 3,
    breakout_atr_mult: float = 0.25,
    atr_period: int = 14,
    target_r_mult: float = 2.0,
    breakeven_r_mult: float = 1.0,
    chandelier_period: int = 22,
    chandelier_mult: float = 3.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    n = len(df)
    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()

    ema = df["close"].ewm(span=ema_period, adjust=False).mean().to_numpy()
    atr = _atr(df, atr_period).to_numpy()
    chand_highest = df["high"].rolling(chandelier_period).max().to_numpy()
    chand_atr = _atr(df, chandelier_period).to_numpy()

    pos = np.zeros(n, dtype=int)

    in_pos = False
    entry_idx = -1
    entry_price = np.nan
    initial_stop = np.nan
    target_price = np.nan
    r_value = np.nan
    breakeven_hit = False
    active_stop = np.nan

    down_run_len = 0
    pullback_group_low = np.nan

    for i in range(n):
        uptrend = (not np.isnan(ema[i])) and close[i] > ema[i]

        if in_pos:
            held = i - entry_idx
            # update breakeven / chandelier trail using bar i's high (favorable move)
            if not breakeven_hit and high[i] - entry_price >= breakeven_r_mult * r_value:
                breakeven_hit = True
                active_stop = max(active_stop, entry_price)
            if breakeven_hit and not np.isnan(chand_highest[i]) and not np.isnan(chand_atr[i]):
                chand_stop = chand_highest[i] - chandelier_mult * chand_atr[i]
                active_stop = max(active_stop, chand_stop)

            exit_now = False
            if close[i] <= active_stop:
                exit_now = True
            elif close[i] >= target_price:
                exit_now = True
            elif held >= max_hold_days:
                exit_now = True

            if exit_now:
                in_pos = False
            else:
                pos[i] = 1

        if not in_pos:
            # track pullback runs while in an established uptrend
            if uptrend and i > 0 and close[i] < close[i - 1]:
                down_run_len += 1
                pullback_group_low = (
                    low[i] if np.isnan(pullback_group_low) else min(pullback_group_low, low[i])
                )
            elif not uptrend:
                down_run_len = 0
                pullback_group_low = np.nan
            else:
                # up-closing bar: reset run tracking unless we're testing a
                # breakout of an already-qualified pullback group this bar
                pass

            qualified = down_run_len >= pullback_min_bars and not np.isnan(pullback_group_low)
            if qualified and not np.isnan(atr[i]):
                trigger_level = pullback_group_low + breakout_atr_mult * atr[i]
                if close[i] > trigger_level:
                    # entry
                    in_pos = True
                    entry_idx = i
                    entry_price = close[i]
                    initial_stop = pullback_group_low
                    r_value = entry_price - initial_stop
                    if r_value <= 0 or np.isnan(r_value):
                        in_pos = False
                    else:
                        target_price = entry_price + target_r_mult * r_value
                        active_stop = initial_stop
                        breakeven_hit = False
                        down_run_len = 0
                        pullback_group_low = np.nan
                        pos[i] = 1
                else:
                    # reset run after a close (up or still qualifying); simple
                    # daily analog: an up-closing bar that doesn't trigger ends
                    # the run
                    if close[i] >= close[i - 1] if i > 0 else False:
                        down_run_len = 0
                        pullback_group_low = np.nan

    return pd.Series(pos, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    ema_period: int = 50,
    pullback_min_bars: int = 3,
    breakout_atr_mult: float = 0.25,
    atr_period: int = 14,
    target_r_mult: float = 2.0,
    breakeven_r_mult: float = 1.0,
    chandelier_period: int = 22,
    chandelier_mult: float = 3.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        ema_period=ema_period,
        pullback_min_bars=pullback_min_bars,
        breakout_atr_mult=breakout_atr_mult,
        atr_period=atr_period,
        target_r_mult=target_r_mult,
        breakeven_r_mult=breakeven_r_mult,
        chandelier_period=chandelier_period,
        chandelier_mult=chandelier_mult,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
