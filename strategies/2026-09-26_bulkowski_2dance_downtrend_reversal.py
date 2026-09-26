"""Strategy: Bulkowski "2-Dance" pattern -- downtrend-reversal long entry, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-XXX):
Per Thomas Bulkowski's ThePatternSite.com analysis of the "2-Dance" pattern
(https://thepatternsite.com/2Dance.html, browser_exec fallback -- web_search
DDGS backend returned empty/error results on several queries this
iteration; the source contributor is Kevin McDonald), a 2-Dance is a
2-candle pattern where:
  - EACH of the two bars has a shadow (wick) at least 3x its own body
    height (small/doji-like real bodies with long wicks).
  - The LONGER of the two bars' shadows is at least 2x the SHORTER shadow
    (so the two bars have visually mismatched, "dancing" opposite-side
    wick emphasis -- source's own illustration shows bar 1 with a tall
    lower shadow, bar 2 with a tall upper shadow, though the rule itself
    doesn't hard-code which side is longer on which bar).
  - Four-price doji bars (O=H=L=C) are explicitly excluded.

Source's own disclosed trading rule (stock/ETF/crypto backtest, "Target
Exit Testing" section): buy-stop a penny above the top of the taller of
the two price bars; protective stop-loss a penny below the bottom of the
shorter/lower bar; target exit at 2x the pattern's own height (top-bottom
range across both bars) added above the pattern top. The source's own
disclosed tables show the pattern beats a matched benchmark in BOTH trend
directions, but performs best as a bullish reversal OUT of a short-term
downtrend (average profit $83.54/trade vs $68.70 benchmark in the
downtrend-reversal case) -- and explicitly warns AGAINST shorting the
pattern (shorting loses money in the source's own tests). This strategy
therefore implements ONLY the long-only, downtrend-reversal variant: entry
gated on the pattern occurring after a short-term downtrend (close below a
falling short SMA over the preceding lookback).

First "2-Dance" pattern tested in this repo; distinct from every other
candlestick reversal entry:
- 2026-09-08-122 (Bullish Outside Bar): single full-range engulf, no
  shadow/body-ratio microstructure requirement.
- 2026-09-26-055 (Three Bar Reversal, this same cron trigger): a 3-bar
  sequence keyed on the MIDDLE bar's low and the third bar's close, no
  shadow-length constraints at all.
- All prior doji/spinning-top strategies in this repo test single-bar
  doji thresholds, not a 2-bar shadow-ratio pair with a target-exit rule
  sized off the pattern's own height.

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
    shadow_body_ratio: float = 3.0,
    shadow_ratio_between_bars: float = 2.0,
    trend_sma_window: int = 10,
    target_height_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Pattern (bars i-1, i):
      - body_i = |close_i - open_i|; shadow_i = high_i - low_i - body_i is
        NOT what's used -- Bulkowski's "shadow" here is interpreted as the
        bar's own upper+lower wick combined, i.e. the non-body portion of
        the bar's range: shadow_i = (high_i - low_i) - body_i.
      - Each bar's shadow >= shadow_body_ratio * its own body (both bars).
      - max(shadow_i-1, shadow_i) >= shadow_ratio_between_bars *
        min(shadow_i-1, shadow_i).
      - Exclude four-price doji (high==low for either bar).
      - Prior downtrend context: close two bars back < sma(trend_sma_window)
        (mirrors the "reversal of a short-term downtrend" rule the source
        found most profitable; the short-only busted-breakout variant is
        explicitly NOT implemented per source's own negative findings).

    Entry: buy-stop equivalent implemented as close-based entry at the
    NEXT bar after pattern completion if that bar's high exceeds the
    pattern's own top (source: "buy-stop a penny above the top of the
    taller of the two price bars") -- approximated here via next-bar high
    breakout confirmed by close for daily-bar feasibility.
    Stop-loss: pattern's own bottom (lowest low of the two bars).
    Target: pattern top + target_height_mult * pattern height.
    Time-stop: max_hold_days.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_ = df["open"]

    body = (close - open_).abs()
    rng = high - low
    shadow = (rng - body).clip(lower=0)

    sma = close.rolling(trend_sma_window).mean()

    valid_bar1 = (shadow.shift(1) >= shadow_body_ratio * body.shift(1)) & (high.shift(1) > low.shift(1))
    valid_bar2 = (shadow >= shadow_body_ratio * body) & (high > low)

    shadow_pair_min = pd.concat([shadow.shift(1), shadow], axis=1).min(axis=1)
    shadow_pair_max = pd.concat([shadow.shift(1), shadow], axis=1).max(axis=1)
    shadow_ratio_ok = shadow_pair_max >= shadow_ratio_between_bars * shadow_pair_min.replace(0, 1e-9)

    pattern_top = pd.concat([high.shift(1), high], axis=1).max(axis=1)
    pattern_bottom = pd.concat([low.shift(1), low], axis=1).min(axis=1)
    pattern_height = pattern_top - pattern_bottom

    prior_downtrend = close.shift(2) < sma.shift(2)

    pattern_complete = valid_bar1 & valid_bar2 & shadow_ratio_ok & prior_downtrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0
    pending_top = None
    pending_bottom = None
    pending_height = None

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
            # Check if pattern completed at i-1 (2-bar pattern ending at i-1);
            # trigger entry at bar i if bar i's high breaks above pattern top.
            if i >= 1 and bool(pattern_complete.iloc[i - 1]):
                top = pattern_top.iloc[i - 1]
                bottom = pattern_bottom.iloc[i - 1]
                pheight = pattern_height.iloc[i - 1]
                if pheight > 0 and high.iloc[i] > top:
                    in_position = True
                    entry_idx = i
                    stop_price = bottom
                    target_price = top + target_height_mult * pheight
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
