"""Strategy: Overnight-gap fade (mean reversion of the intraday gap).

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary of gap-fade mean-reversion writeups
(JournalPlus/Tickerly/StockAlarm cited in the overview; read via
`browser_exec` fallback after `web_search`'s DDGS backend failed with the
same Yahoo/TLS RequestError as this iteration's earlier query): when a
stock/ETF opens significantly higher or lower than the prior session's
close (a "gap"), absent a major fundamental catalyst, the opening move
tends to partially reverse ("fade") back toward the prior close during that
same session, because the gap frequently overshoots on order-flow noise
rather than genuine new information. The source's own rules are intraday
(scan for 1-4% gaps, wait 15 minutes after the open, short gap-ups /
long gap-downs, exit by a mid-morning time-stop) and require intraday
(sub-daily) bar data this repo's `data/loaders.py` does not provide for
equities. This implementation adapts the same economic mechanism to the
DAILY-bar interface actually available here: using the day's own OHLC
(open, high, low, close all present in one daily bar), take a fade
position established AT THE OPEN and held to THAT SAME DAY's CLOSE only
(not held overnight into the next gap) whenever the day's gap
(open vs. prior close, as a fraction) exceeds `gap_threshold` in either
direction -- short the gap-up (bet on fade-down to close), long the
gap-down (bet on fade-up to close). This is a genuinely different
construction from every other overnight/gap strategy already in this repo
(all of which trade the OVERNIGHT return itself, i.e. hold close-to-open;
this strategy instead trades the INTRADAY open-to-close return in the
gap's fade direction, and is flat overnight) -- first "gap fade"/intraday
mean-reversion-of-the-open entry in this repo (0 prior matches in
knowledge_base/strategies_index.jsonl for "gap fade").

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (position series,
        -1/0/+1, held only for the trading day the gap occurred on)
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns, using SAME-DAY open-to-close return times the fade
        position -- this strategy is flat overnight by construction, so no
        shift(1) is applied; the position for day t is knowable at day t's
        open using only day t's open and day t-1's close, both already
        public information at that point).
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
    gap_threshold: float = 0.01,
    max_gap_threshold: float = 0.06,
    allow_short: bool = True,
) -> pd.Series:
    """Fade position for the day the gap occurs on: -1 (short) if gap up
    beyond `gap_threshold`, +1 (long) if gap down beyond `gap_threshold`,
    0 otherwise. Gaps larger than `max_gap_threshold` are excluded (avoid
    fading likely-fundamental/news-driven gaps per the source's own
    "check catalysts" filter, approximated here by an upper size cutoff
    since this repo has no news/catalyst feed)."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    prior_close = close.shift(1)

    gap = (open_ - prior_close) / prior_close

    long_gapdown = (gap < -gap_threshold) & (gap > -max_gap_threshold)
    short_gapup = (gap > gap_threshold) & (gap < max_gap_threshold)

    position = pd.Series(0.0, index=df.index)
    position[long_gapdown] = 1.0
    if allow_short:
        position[short_gapup] = -1.0

    return position.fillna(0.0)


def generate_returns(
    price_df: pd.DataFrame,
    gap_threshold: float = 0.01,
    max_gap_threshold: float = 0.06,
    allow_short: bool = True,
) -> pd.Series:
    """Same-day open-to-close return times the fade position (no
    shift(1): position for day t is determined by day t's own open,
    known at market-open on day t, and held only intraday to day t's
    close -- flat overnight)."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    position = generate_signals(
        price_df,
        gap_threshold=gap_threshold,
        max_gap_threshold=max_gap_threshold,
        allow_short=allow_short,
    )

    intraday_ret = (close - open_) / open_
    strat_ret = position * intraday_ret
    return strat_ret.fillna(0.0)
