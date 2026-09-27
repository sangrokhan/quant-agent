"""Strategy: PDH/L FVG (CRT) -- Previous Day High/Low liquidity sweep
confirmed by a Fair Value Gap, daily-bar adaptation.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per LuxAlgo's "PDH/L FVG (CRT)" indicator
(https://www.luxalgo.com/library/indicator/pdh-l-fvg-crt, published Aug 11
2026, read this iteration via browser_exec -- web_search DDGS backend
returned no results for the initial keyword queries this iteration). The
source's own disclosed mechanism ("wait for price to sweep a Previous Day
High (PDH) or Previous Day Low (PDL). Once a sweep occurs, the indicator
looks for a qualifying Fair Value Gap (FVG) to emerge within the specified
window of bars... Trend Filtering: Enable the EMA filter to ensure that
signals align with the broader market direction"): a liquidity sweep below
a recent swing-low-of-days (multi-day PDL) followed by a bullish 3-bar Fair
Value Gap (a gap that stays unfilled by the surrounding wicks) forming
within a short lookback window is treated as a trend-continuation entry
trigger, gated by an EMA trend filter. This is a distinct combination from
prior FVG entries in this repo (id 2026-09-08-018 tests a plain FVG-fill
mean-reversion idea; 2026-09-24-051/052/053 test EQL-liquidity-zone+FVG
without any PDH/PDL daily-swing-level component) -- the defining feature
here is specifically anchoring the swept level to the PRIOR TRADING DAY's
own high/low (rather than an arbitrary N-bar pivot/equal-lows zone) before
requiring the FVG confirmation.

Signal logic (long side only, daily-bar adaptation)
----------------------------------------------------
- PDL = the prior trading day's own low (shift(1) of daily low). A "sweep"
  is a bar whose low trades below PDL (liquidity grab below support).
- Within `fvg_search_window` bars after (and including) the sweep bar, look
  for a bullish 3-bar Fair Value Gap: bar[k-2].high < bar[k].low (an
  unfilled gap between the first and third candle of a 3-bar sequence).
- Entry: on the bar the qualifying FVG completes (bar k), if close is above
  EMA(trend_window) (source's own "Trend Filtering" option), enter long.
- Optional 50%-retest entry mode (`use_retest_entry`): instead of entering
  immediately on FVG completion, wait up to `retest_window` further bars for
  price to trade back down to the FVG midpoint before entering (source's
  "conservative approach... waits for a 50 percent retest of the FVG
  midpoint").
- Exit: max_hold_days time-stop, or close falling back below the FVG's own
  lower boundary (invalidation of the gap).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def generate_signals(
    price_df: pd.DataFrame,
    fvg_search_window: int = 8,
    trend_window: int = 100,
    trend_filter: bool = True,
    use_retest_entry: bool = False,
    retest_window: int = 5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    pdl = low.shift(1)  # previous day's low
    ema_trend = close.ewm(span=trend_window, adjust=False).mean()
    uptrend = (close > ema_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    fvg_lower = None

    i = 2
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = fvg_lower is not None and close.iloc[i] < fvg_lower
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        if pd.isna(pdl.iloc[i]):
            i += 1
            continue

        # Sweep: this bar's low trades below the previous day's low.
        if low.iloc[i] < pdl.iloc[i]:
            swept_idx = i
            # Search forward (including the sweep bar itself as bar k-2 origin)
            # for a bullish 3-bar FVG: bar[k-2].high < bar[k].low.
            found_entry = None
            found_fvg_lower = None
            for k in range(swept_idx + 2, min(swept_idx + 2 + fvg_search_window, n)):
                if high.iloc[k - 2] < low.iloc[k]:
                    # Bullish FVG detected, gap zone = (high[k-2], low[k])
                    gap_lo = high.iloc[k - 2]
                    if not bool(uptrend.iloc[k]):
                        continue
                    if use_retest_entry:
                        gap_mid = (gap_lo + low.iloc[k]) / 2.0
                        for r in range(k + 1, min(k + 1 + retest_window, n)):
                            if low.iloc[r] <= gap_mid:
                                if bool(uptrend.iloc[r]):
                                    found_entry = r
                                    found_fvg_lower = gap_lo
                                break
                        if found_entry is not None:
                            break
                    else:
                        found_entry = k
                        found_fvg_lower = gap_lo
                        break

            if found_entry is not None:
                in_position = True
                entry_idx = found_entry
                fvg_lower = found_fvg_lower
                i = found_entry
                position.iloc[i] = 1
                i += 1
                continue

        position.iloc[i] = 0
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
