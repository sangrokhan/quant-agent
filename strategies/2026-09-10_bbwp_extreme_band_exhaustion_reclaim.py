"""Strategy: Triple-Bollinger-Band / BBWP extreme-volatility exhaustion-reclaim
long-only mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this file's entry):
Per Google AI-overview synthesis (TradingView/CrossTrade/TrendSpider/Colibri
Trader/tmgm.com consensus, fetched via browser_exec after web_search's DDGS
backend failed 3x this iteration with TLS connection errors): during periods
of EXTREME volatility expansion (Bollinger Band Width Percentile, BBWP, at or
above its own trailing 100-bar high), a close that punches outside the -3
std-dev outer Bollinger Band and then reclaims back above the -2 std-dev band
on the very next bar signals that panic-selling exhaustion has completed and
a short-term mean-reversion bounce toward the basis (SMA) is likely. This is
distinct from this repo's already-tested BBWP squeeze-BREAKOUT strategy
(2026-09-07-003, id triggers on LOW BBWP i.e. volatility contraction preceding
a continuation breakout) -- here the mechanism is the opposite tail: HIGH
BBWP (volatility already extreme) triggering a reversion FADE of the extreme
move, gated by a long-term uptrend filter so we only fade dips within an
established bull regime (not catching a falling knife in a structural
downtrend).

Signal logic (long-only)
-------------------------
- 200-day EMA defines the macro trend filter: only take entries when close is
  above a RISING 200-day EMA (avoids fading extreme selloffs in downtrends).
- Bollinger basis = SMA(bb_window), std = rolling std(bb_window).
- BBWP = rolling percentile rank of the current band width
  ((upper2-lower2)/basis) against its own trailing bbwp_lookback-bar history,
  in [0, 100].
- Entry: BBWP >= bbwp_threshold (extreme volatility expansion already
  present) AND the PRIOR bar closed below the -3 std lower band AND the
  CURRENT bar's close has reclaimed back above the -2 std lower band.
- Exit: close crosses back above the basis (SMA) -- the classic
  mean-reversion target -- OR a max_hold_days time-stop backstop (source
  doesn't disclose an explicit max hold, but every mean-reversion strategy in
  this repo uses one to avoid indefinite unwind-less holds).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    bb_window: int = 20,
    bbwp_lookback: int = 100,
    bbwp_threshold: float = 90.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_trend = close.ewm(span=trend_window, adjust=False).mean()
    trend_up = (close > ema_trend) & (ema_trend > ema_trend.shift(5))

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()

    lower2 = sma - 2.0 * std
    lower3 = sma - 3.0 * std

    band_width = (2.0 * 2.0 * std) / sma  # (upper2-lower2)/basis proxy
    bbwp = band_width.rolling(bbwp_lookback, min_periods=max(20, bbwp_lookback // 4)).rank(pct=True) * 100.0

    prior_below_3sd = close.shift(1) < lower3
    reclaim_above_2sd = close > lower2
    extreme_vol = bbwp >= bbwp_threshold

    entry_signal = extreme_vol & prior_below_3sd & reclaim_above_2sd & trend_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = close.index

    for i in range(len(idx_list)):
        if not in_pos:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held_days = i - entry_idx
            exit_meanrev = close.iloc[i] > sma.iloc[i]
            exit_timeout = held_days >= max_hold_days
            if exit_meanrev or exit_timeout:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bbwp_lookback: int = 100,
    bbwp_threshold: float = 90.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        bb_window=bb_window,
        bbwp_lookback=bbwp_lookback,
        bbwp_threshold=bbwp_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
