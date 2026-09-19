"""Strategy: Bitcoin trading-session filter — long during Asian+European
hours, flat during the US session.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-020):
Multiple sources (Faisal Khan's "Visualizing BTC cumulative returns by
trading sessions" Medium analysis, and corroborating market commentary
e.g. Yahoo Finance "Why Does Asia Keep Buying Bitcoin While Americans Are
[Selling]") report a persistent session-level asymmetry in BTC returns:
US trading hours (approx 13:00-22:00 UTC, the US session per standard
crypto-session convention used by TMGM/Binance/TradingView session guides)
have shown negative-to-flat cumulative returns over multi-month/YTD windows
in several cited periods, while Asian (00:00-08:00 UTC) and European
(08:00-13:00 UTC) session hours have captured most of BTC's positive drift
-- plausibly reflecting differential regional risk appetite/selling
pressure (US institutional profit-taking/hedging flows vs Asian retail
accumulation).

This repo has NOT previously tested an intraday session-of-day filter on
BTC (existing calendar-effect entries cover day-of-week/weekend/month/
holiday effects, but not intraday UTC-hour session boundaries) -- this is
directly testable since data/loaders.py's load_crypto returns native
hourly OHLCV bars for BTC/USDT via ccxt, unlike the equity daily-bar-only
constraint that blocks most other intraday ideas in this repo.

Signal logic
------------
- Each hourly bar's UTC hour-of-day is classified into one of three
  sessions using boundaries from TMGM/Binance/TradingView session guides:
    Asian:    session_asian_start <= hour < session_european_start (default 0-8 UTC)
    European: session_european_start <= hour < session_us_start (default 8-13 UTC)
    US:       session_us_start <= hour < 24 (default 13-24 UTC)
- Long (position=1) during Asian and European session hours; flat during
  US session hours (the hypothesized weak/negative-return window).
- No additional trend/regime filter -- this is a pure intraday session-time
  filter, testing the calendar-anomaly hypothesis in isolation (consistent
  with this repo's existing day-of-week/holiday calendar-effect strategies,
  which are similarly tested unconditionally before adding regime gates in
  follow-up iterations if a near-miss is found).
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
    session_asian_start: int = 0,
    session_european_start: int = 8,
    session_us_start: int = 13,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on UTC hour-of-day session."""
    df = _prep(price_df)
    idx = df.index
    hours = idx.hour if hasattr(idx, "hour") else pd.DatetimeIndex(idx).hour

    hours = pd.Series(hours, index=df.index)

    def in_session(h: int) -> bool:
        # US session hours are the "flat" window; everything else (Asian +
        # European) is long.
        if session_us_start <= session_asian_start:
            # degenerate config guard, treat as always-long
            return True
        if session_us_start < 24:
            us_session = (h >= session_us_start) and (h < 24)
        else:
            us_session = False
        return not us_session

    position = hours.apply(lambda h: 1 if in_session(int(h)) else 0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted returns at native bar frequency (no transaction costs).

    Note: since the position can flip every single hourly bar (a fixed
    time-of-day filter, not a momentum/trend signal), no shift-by-1-day
    look-ahead-avoidance logic applies here in the same way as daily-bar
    strategies -- we still shift by one bar to avoid trading on the same
    bar's own close-to-close return, consistent with this repo's standard
    convention.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    bar_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * bar_ret
    return strategy_ret
