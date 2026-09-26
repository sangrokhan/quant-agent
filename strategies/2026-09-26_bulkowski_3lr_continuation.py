"""Strategy: Bulkowski "3L-R" (Three Lows-Reversal), continuation-context, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-XXX):
Per Thomas Bulkowski's ThePatternSite.com analysis of the "3L-R" pattern
(https://thepatternsite.com/3L-R.html, browser_exec fallback -- web_search
DDGS backend returned empty/error results on multiple queries this
iteration; source credits Traders.com/Paolo Pezzutti/Michael Harris), a
4-bar pattern forms when:
  - Bars 1, 2, 3 have consecutively LOWER lows (low[1] > low[2] > low[3];
    highs are irrelevant for these three bars).
  - Bar 4 (the reversal bar) has a HIGH that closes above bar 1's high.

Source's own disclosed trading rule: buy at the OPEN the day after bar 4
completes. Two exit variants were both source-tested: (a) a fixed 7%
profit target / 7% stop-loss (per the Traders.com article this pattern
was originally sourced from), and (b) a "pattern stop" -- a penny below
the pattern's own lowest low (bar 3's low), with a measure-rule target
(pattern height added to bar-4's high). This strategy implements variant
(b) (pattern-based stop + measure-rule target) as the primary rule, since
it's scale-invariant across assets/regimes unlike a flat 7%, with the
flat-percent variant available via a `use_fixed_pct_exit` toggle for
completeness.

Distinctive per source's OWN stats: the pattern actually performs BETTER
as a CONTINUATION (traded when price was already rising into the pattern)
than as a reversal of a downtrend (9% avg gain vs 8%) -- despite "3L-R"
notionally suggesting a reversal setup, the source's own backtest favors
trading it as a pullback-in-an-uptrend continuation. This strategy
therefore gates entries on a PRIOR UPTREND context (close above a rising
SMA), the opposite trend-filter direction from typical reversal patterns
tested elsewhere in this repo.

First 4-bar "three-lower-lows-then-reversal-bar" pattern tested in this
KB; distinct from:
- 2026-09-26-055 (Three Bar Reversal, this cron trigger): a 3-bar pattern
  keyed on the MIDDLE bar being the extreme low, downtrend-context gated.
- 2026-09-26-056 (Bulkowski 2-Dance): a 2-bar shadow/body-ratio pattern,
  no monotonic-lower-lows requirement.
- All prior triple-bottom/W-pattern entries (2026-09-09-045 etc.): those
  require the three lows to be roughly EQUAL (a support test), not
  strictly monotonically declining.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    trend_sma_window: int = 20,
    target_height_mult: float = 1.0,
    max_hold_days: int = 20,
    use_fixed_pct_exit: bool = False,
    fixed_pct: float = 0.07,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Pattern (bars i-3, i-2, i-1, i):
      - low[i-3] > low[i-2] > low[i-1]  (3 consecutively lower lows)
      - high[i] > high[i-3]             (bar 4's high above bar 1's high)
      - prior uptrend context: close[i-3] > sma(trend_sma_window) at i-3
        (source's own finding: continuation-in-uptrend outperforms
        reversal-of-downtrend for this specific pattern)

    Entry: buy at the open of the bar AFTER pattern completion (bar i+1),
    approximated here as entering at close of bar i+1 for daily-bar
    feasibility (consistent with this repo's other next-bar-open-entry
    strategies).
    Stop-loss: pattern's lowest low (bar i-1's low, per source's "pattern
    stop" variant) OR fixed_pct below entry if use_fixed_pct_exit.
    Target: bar i's high + target_height_mult * pattern height (measure
    rule) OR fixed_pct above entry if use_fixed_pct_exit.
    Time-stop: max_hold_days.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    sma = close.rolling(trend_sma_window).mean()

    lower_lows = (low.shift(3) > low.shift(2)) & (low.shift(2) > low.shift(1))
    higher_high = high > high.shift(3)
    prior_uptrend = close.shift(3) > sma.shift(3)

    pattern_complete = lower_lows & higher_high & prior_uptrend.fillna(False)

    pattern_low = low.shift(1)  # bar 3's low (lowest of the pattern)
    pattern_high = high  # bar 4's high
    pattern_height = pattern_high - pattern_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            px = close.iloc[i]
            hit_stop = px <= stop_price
            hit_target = px >= target_price
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            # Pattern completes at bar i-1; entry at bar i (the day after).
            if i >= 1 and bool(pattern_complete.iloc[i - 1]):
                plow = pattern_low.iloc[i - 1]
                phigh = pattern_high.iloc[i - 1]
                pheight = pattern_height.iloc[i - 1]
                if pheight > 0:
                    in_position = True
                    entry_idx = i
                    entry_price = close.iloc[i]
                    if use_fixed_pct_exit:
                        stop_price = entry_price * (1 - fixed_pct)
                        target_price = entry_price * (1 + fixed_pct)
                    else:
                        stop_price = plow
                        target_price = phigh + target_height_mult * pheight
                    position.iloc[i] = 1
                else:
                    position.iloc[i] = 0
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
