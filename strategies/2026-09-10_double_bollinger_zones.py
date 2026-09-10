"""Strategy: Double Bollinger Zones (DBB) regime trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-130):
Per https://www.luxalgo.com/library/indicator/double-bollinger-zones/
(visited this iteration): two Bollinger Band pairs share one 20-period SMA
basis -- inner bands at 1 standard deviation, outer bands at 2 standard
deviations. The "buy zone" is the region between the inner and outer upper
bands. Per the source's own disclosed rules:
  - "Uptrend qualified": the required run of consecutive closes (default 2)
    holds within the buy zone -- "territory to follow, not stretch to fade".
  - "Zone lost": a close back inside the inner band drops the regime to
    neutral (the source's own stated first warning/exit signal).
  - "Pullback holds the floor": an intrabar touch of the inner band that
    still closes back inside the buy zone keeps the regime alive (source
    describes this as a continuation entry point, not implemented as a
    separate re-entry trigger here -- the exit rule above already keeps the
    position open in this case since only a CLOSE inside the inner band
    drops the regime).

Operationalized rule: long entry when confirmation_closes consecutive
closes have held strictly between the inner-upper and outer-upper bands
(qualifying the uptrend regime); exit when a close falls back inside (below)
the inner-upper band (zone lost), or a max_hold_days time-stop safety
backstop (source gives no explicit hold-period rule).

First Double Bollinger Band / Double Bollinger Zones strategy in this repo
(0 prior hits for "Double Bollinger" in the index) -- distinct from all
prior single-pair Bollinger Band mean-reversion/squeeze/band-walk/%B
strategies, which use only ONE band pair rather than a two-tier
inner/outer zone system.

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
    bb_window: int = 20,
    inner_std: float = 1.0,
    outer_std: float = 2.0,
    confirmation_closes: int = 2,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    inner_upper = sma + inner_std * std
    outer_upper = sma + outer_std * std

    in_buy_zone = (close > inner_upper) & (close <= outer_upper)
    # Count consecutive True runs of in_buy_zone.
    run_len = in_buy_zone.astype(int).groupby(
        (~in_buy_zone).cumsum()
    ).cumsum()
    uptrend_qualified = in_buy_zone & (run_len >= confirmation_closes)

    zone_lost = close <= inner_upper  # close back inside/below inner band

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(zone_lost.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(uptrend_qualified.iloc[i]):
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
