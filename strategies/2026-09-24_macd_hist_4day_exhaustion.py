"""Strategy: MACD-Histogram 4-Day Declining-Momentum Exhaustion (mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-078):
Per QuantifiedStrategies.com's "MACD Histogram Trading Strategy" (accessed via
Google AI-overview cached snippet, browser_exec fallback -- web_search DDGS
backend errored on this iteration's query), a mean-reversion long entry fires
when the standard MACD(12,26,9) histogram has been falling for
`hist_decline_days` consecutive bars AND the histogram value
`hist_decline_days` bars ago was already negative (confirming a sustained,
not just noisy, decline) AND today's close is below yesterday's close
(price confirmation of the exhaustion). The idea: after a multi-day
deceleration streak of bearish momentum plus a fresh down-close, the
selling pressure is exhausted and a short-term bounce is likely. Exit
("QS exit" per source) on the first close that closes above the PRIOR
day's high (any pop signals the bounce has happened), backstopped here by
a max_hold_days time-stop (source doesn't specify one, added for risk
control consistent with every other mean-reversion strategy in this repo).

Distinct from every other MACD-family strategy already tested here
(2026-09-04-064 Elder Impulse trend-following, 2026-09-04-100 histogram
inflection-point (single day), 2026-09-04-161 MACD+RSI combo) because this
one requires a MULTI-DAY (4-bar) declining-histogram streak with a
below-zero anchor point as its entry trigger, not a single-bar crossover
or inflection.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd_hist(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    hist_decline_days: int = 4,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    hist = _macd_hist(close, fast, slow, signal)

    # Histogram falling for hist_decline_days consecutive bars: each of the
    # last hist_decline_days diffs must be negative.
    hist_diff = hist.diff()
    declining_streak = hist_diff.lt(0)
    streak_ok = declining_streak.rolling(hist_decline_days).sum() == hist_decline_days

    hist_anchor_negative = hist.shift(hist_decline_days) < 0
    price_down = close < close.shift(1)

    entry = streak_ok.fillna(False) & hist_anchor_negative.fillna(False) & price_down.fillna(False)

    prior_high = high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_qs = close.iloc[i] > prior_high.iloc[i] if pd.notna(prior_high.iloc[i]) else False
            if bool(exit_qs) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
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
