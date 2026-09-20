"""Strategy: Asian-session-range breakout traded during the London session
(hourly-bar crypto adaptation of the classic FX "London Breakout" strategy).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-169):
Per QuantifiedStrategies.com's "London Breakout Strategy" (freely available,
https://www.quantifiedstrategies.com/london-breakout-strategy/), the
Asian trading session (roughly 00:00-08:00 UTC) establishes a
support/resistance range; when the London session opens (~08:00 UTC), a
breakout above/below that range signals a likely continuation for the
rest of the trading day, driven by London's outsized share of trading
volume/liquidity. The source's own EUR/USD backtest results were mixed
(often lossy without added filters), so this strategy tests the concept
honestly on this repo's 24h crypto markets (BTC/USDT, ETH/USDT) using
hourly OHLCV via `load_crypto` -- the FX-specific session concept adapts
naturally to crypto since crypto trades continuously and genuinely has
volume/volatility patterns tied to Asian/European/US trading-desk hours.
0 prior "first hour range"/"Asian session"/"London session" entries in
this repo -- distinct from the existing first/last-hour sign-prediction
strategy (2026-09-19-054, a different intraday mechanism entirely). Not
tested on equity (daily-bar-only via yfinance in this repo's loaders --
no genuine intraday session structure available for QQQ/SPY at the
required hourly resolution over a multi-year sample), consistent with
RESEARCH_LOOP.md's allowance for asset-class-scoped honesty when a
strategy is fundamentally intraday/session-based and equity intraday data
isn't available cache-first.

Signal logic
------------
- Each UTC calendar day's Asian session is defined as hours
  [asian_start_hour, asian_end_hour) (default 0-8 UTC). The session range
  is high()/low() over those hours.
- During the London session window [asian_end_hour, london_end_hour)
  (default 8-16 UTC) of the SAME calendar day, go long the first hour the
  close breaks above the Asian session's high by more than breakout_pct.
  (Short breakouts are not traded -- long-only per SAFETY.md scope.)
- Exit: at the close of the last London-session hour of that day
  (london_end_hour), or when a max_hold_bars cap is reached, whichever
  first (keeps the trade contained to that day's session per the
  strategy's own day-trading framing).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_hourly(df: pd.DataFrame) -> bool:
    """This strategy fundamentally requires sub-daily (hourly) bars to
    define an Asian/London session split. On daily-bar data (e.g. equity
    via load_equity, or the grid-test harness's forced interval="1d" call
    path -- see validation/grid_test.py's own documented interval-forcing
    behavior) there is only one bar per day, so no session split is
    possible. Returns an all-flat/no-trade series in that case (an
    expected "not applicable" result, consistent with the pattern already
    used by strategies/2026-09-11_crypto_session_split_momentum_reversal.py
    for the same not-applicable-on-daily-bars situation)."""
    if len(df) < 3:
        return False
    hours = pd.Series(df.index).dt.hour
    return hours.nunique() > 1


def generate_signals(
    price_df: pd.DataFrame,
    asian_start_hour: int = 0,
    asian_end_hour: int = 8,
    london_end_hour: int = 16,
    breakout_pct: float = 0.002,
    max_hold_bars: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series (hourly bars)."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    if not _is_hourly(df):
        return pd.Series(0, index=idx, dtype=int)

    close = df["close"]
    high = df["high"]

    hour = idx.hour
    cal_day = idx.normalize()

    asian_mask = (hour >= asian_start_hour) & (hour < asian_end_hour)
    london_mask = (hour >= asian_end_hour) & (hour < london_end_hour)

    # Per-calendar-day Asian session high, broadcast back to every bar of
    # that same day.
    asian_high_by_day = high.where(asian_mask).groupby(cal_day).transform("max")

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_bars = i - entry_i
            session_over = not bool(london_mask[i])
            if session_over or hold_bars >= max_hold_bars:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(london_mask[i]):
                asian_high = asian_high_by_day.iloc[i]
                if pd.notna(asian_high) and close.iloc[i] > asian_high * (1 + breakout_pct):
                    in_position = True
                    entry_i = i
                    position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    asian_start_hour: int = 0,
    asian_end_hour: int = 8,
    london_end_hour: int = 16,
    breakout_pct: float = 0.002,
    max_hold_bars: int = 8,
) -> pd.Series:
    """Bar-level strategy returns (hourly bars; no transaction costs applied
    here)."""
    df = _prep(price_df)
    close = df["close"]
    bar_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asian_start_hour=asian_start_hour,
        asian_end_hour=asian_end_hour,
        london_end_hour=london_end_hour,
        breakout_pct=breakout_pct,
        max_hold_bars=max_hold_bars,
    )
    strat_ret = bar_ret * position.shift(1).fillna(0)
    return strat_ret
