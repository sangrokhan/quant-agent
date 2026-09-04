"""Strategy: Larry Connors %B mean-reversion (Bollinger %B < 0, exit on
quick recovery), gated by a 200-day uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-107):
Per QuantifiedStrategies.com's "2 Simple Mean Reversion Trading Strategies"
article (Larry Connors' %B strategy): in a long-term uptrend (price above
its 200-day SMA), a close where Bollinger %B drops below 0 (i.e. the close
is below the LOWER Bollinger Band -- %B=0 means "exactly at the lower
band", and %B<0 means the close has pierced below it) signals a
short-term overextension worth a mean-reversion long entry. Exit on a
quick recovery (source's own SPY backtest, 1993-present: 63 trades, 89%
win rate, profit factor 3, only 4% time invested, MDD -8%). This repo
operationalizes "quick recovery" as %B crossing back above an
`exit_pct_b` threshold (default 0.5, the middle band).

%B is a NORMALIZED band-position oscillator distinct from every other
Bollinger-family strategy already tested in this repo (2026-09-03-001,
-023; 2026-09-04-067; 2026-09-04-046 SD-channel; 2026-09-04-091 TTM
squeeze) -- those all threshold on the RAW close price vs. the raw band
level or a rolling percentile of band WIDTH, whereas %B = (close -
lower_band) / (upper_band - lower_band) normalizes WHERE price sits within
the band, bounded roughly 0-1 in typical conditions (can exceed the range
during a genuine breakout).

Signal logic
------------
- rolling_mean = SMA(close, bb_window), rolling_std = STD(close,
  bb_window).
- upper_band = rolling_mean + bb_std * rolling_std
- lower_band = rolling_mean - bb_std * rolling_std
- pct_b = (close - lower_band) / (upper_band - lower_band)
- Trend filter: close > SMA(close, trend_window), default 200.
- Entry (long): pct_b crosses below entry_pct_b (default 0.0), while the
  trend filter passes.
- Exit: pct_b crosses back above exit_pct_b (default 0.5, the band
  midline).
- Long-only, flat otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    trend_window: int = 200,
    entry_pct_b: float = 0.0,
    exit_pct_b: float = 0.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_mean = close.rolling(bb_window).mean()
    rolling_std = close.rolling(bb_window).std()
    upper_band = rolling_mean + bb_std * rolling_std
    lower_band = rolling_mean - bb_std * rolling_std
    band_width = upper_band - lower_band
    pct_b = (close - lower_band) / band_width

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    pct_b_prev = pct_b.shift(1)
    entry_trigger = (pct_b < entry_pct_b) & (pct_b_prev >= entry_pct_b) & trend_ok.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(n):
        pb = pct_b.iloc[i]
        if in_pos:
            position.iloc[i] = 1
            if pd.notna(pb) and pb >= exit_pct_b:
                in_pos = False
        else:
            if bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False:
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    trend_window: int = 200,
    entry_pct_b: float = 0.0,
    exit_pct_b: float = 0.5,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, bb_window=bb_window, bb_std=bb_std, trend_window=trend_window,
        entry_pct_b=entry_pct_b, exit_pct_b=exit_pct_b,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
