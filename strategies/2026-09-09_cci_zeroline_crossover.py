"""Strategy: plain CCI zero-line crossover trend-following (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-083):
Per Pomegra's "CCI Zero Line Crossover: Trend-Following with the Commodity
Channel Index" article and TITAN FX Research Hub ("When CCI crosses the
zero line, it signals a potential trend reversal and can serve as a
reference point for trade entries"), surfaced via Google search snippet
(the Pomegra page itself 404'd on direct navigation), CCI crossing above
zero from below signals a fresh uptrend worth a long entry. This is a
DISTINCT rule from every other CCI variant already tested in this repo:
oversold mean-reversion at CCI<-90 (2026-09-04-024), momentum-breakout at
CCI>+100 (2026-09-04-072), Woodie's Zero-Line-Reject bounce-without-cross
(2026-09-05-007), Woodie's trend-line break (2026-09-06-160), CCI
range-reentry (2026-09-08-088), Woodie's hook-from-extreme (2026-09-09-061)
-- none of those use the plain unconditional zero-line CROSS itself as the
entry trigger.

Signal logic
------------
- CCI(cci_window), standard construction: (typical_price - SMA(typical_price))
  / (0.015 * mean_absolute_deviation(typical_price)).
- Entry (long): CCI crosses from <=0 to >0 (fresh bullish cross).
- Exit: CCI crosses back below 0, OR a max_hold_days time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(window).mean()
    mad = typical_price.rolling(window).apply(
        lambda x: (x - x.mean()).abs().mean(), raw=False
    )
    cci = (typical_price - sma_tp) / (0.015 * mad.replace(0, pd.NA))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cci = _cci(df, cci_window)
    prev_cci = cci.shift(1)
    bullish_cross = (cci > 0) & (prev_cci <= 0)
    bearish_cross = (cci < 0) & (prev_cci >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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
