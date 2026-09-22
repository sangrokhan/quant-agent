"""Strategy: TRIX signal-line crossover, gated by a 50/200 EMA trend regime
filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-031):
Source: Google AI Overview synthesis (Korean-language SERP; search "TRIX
indicator signal line crossover trading strategy specific parameters
backtest"), read via browser_exec Google SERP fallback (web_search DDGS
backend errored this iteration). Disclosed standard parameter table:
  - TRIX period = 14 (triple-smoothed EMA rate-of-change oscillator).
  - Signal line = 9-period EMA of TRIX.
  - Optimal timeframe for these standard params: daily bars.
  - Trend filter: 50 EMA / 200 EMA (price above both = bullish regime,
    used to gate entries and avoid false signals in choppy/ranging
    markets).
  - Entry: TRIX line crosses above its signal line (golden cross) AND
    price is above both the 50 EMA and 200 EMA (bullish regime filter).
  - Exit: TRIX line crosses below its signal line (dead cross).
No prior entry in this KB combines "TRIX" with a "signal line" crossover
(checked via strategies_index.jsonl grep: "TRIX signal line" had zero
prior matches; there are 12 generic "TRIX" mentions but none use the
signal-line-crossover + dual-EMA-trend-filter mechanism specifically).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trix(close: pd.Series, window: int) -> pd.Series:
    ema1 = close.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    return ema3.pct_change() * 100


def generate_signals(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 9,
    fast_ema: int = 50,
    slow_ema: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trix = _trix(close, trix_window)
    signal = trix.ewm(span=signal_window, adjust=False).mean()

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    bullish_regime = (close > ema_fast) & (close > ema_slow)

    golden_cross = (trix > signal) & (trix.shift(1) <= signal.shift(1))
    dead_cross = (trix < signal) & (trix.shift(1) >= signal.shift(1))

    entry = golden_cross & bullish_regime

    pos_vals = []
    in_pos = False
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
        elif in_pos and bool(dead_cross.iloc[i]):
            in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 9,
    fast_ema: int = 50,
    slow_ema: int = 200,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trix_window=trix_window,
        signal_window=signal_window,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
