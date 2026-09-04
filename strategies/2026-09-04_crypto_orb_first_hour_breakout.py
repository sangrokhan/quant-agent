"""Strategy: Crypto Opening Range Breakout (ORB), first-hour-of-UTC-day range.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-148):
Toby Crabel's classic Opening Range Breakout concept (mark the high/low of
the first N minutes of a session; a decisive breakout above/below that
range signals which side "won" the initial price-discovery battle and
tends to have follow-through for the rest of the session) is tested here
on BTC/ETH using the first 1-hour UTC candle of each calendar day as the
"opening range" (crypto's 24/7 market has no exchange-defined session open,
so the UTC daily boundary is used as the closest analogue). Long entry when
a subsequent hour's close breaks above the opening-hour's high; exit when
price closes back below the opening-hour's low (failed breakout), or the
UTC day ends (flat overnight, avoiding overnight/weekend gap risk per the
source's session-bound design), or a max_hold_hours time-stop. Source:
tradingcompendium.com ORB explainer (Toby Crabel origin). First ORB-family
strategy in this repo. NOTE: this is deliberately CRYPTO-ONLY -- the
equity data loader here is daily-only (data/loaders.py load_equity has no
intraday granularity), so a true opening-range concept cannot be tested on
equities with the data available; testing scope is narrowed honestly rather
than forcing a daily-bar proxy that wouldn't represent the same idea (a
daily gap-based proxy would just duplicate the already-tested/rejected
gap-fade family, id 2026-09-03-007/010).

Signal logic (crypto, 1h bars, per UTC calendar day)
-----------------------------------------------------
- Each UTC day's first 1h bar defines the opening range (or_high, or_low).
- Entry (long): a later bar within the SAME UTC day closes above or_high
  (breakout_mult can widen the trigger, e.g. 1.002x or_high to filter
  marginal breaks).
- Exit: close drops back below or_low, OR the UTC day changes (flat at
  day boundary, no overnight carry), OR max_hold_hours elapsed since
  entry, whichever comes first.
- Flat otherwise (including the entire opening-range hour itself).
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
    breakout_mult: float = 1.0,
    max_hold_hours: int = 12,
) -> pd.Series:
    df = _prep(price_df)
    day = df.index.normalize()
    df = df.assign(_day=day)

    # Opening range = first bar of each UTC day.
    first_idx = df.groupby("_day").apply(lambda g: g.index[0])
    or_high = df.loc[first_idx, "high"]
    or_low = df.loc[first_idx, "low"]
    or_high.index = first_idx.index  # index by day
    or_low.index = first_idx.index

    day_or_high = df["_day"].map(or_high)
    day_or_low = df["_day"].map(or_low)

    close = df["close"]
    is_opening_bar = df.index.isin(set(first_idx.values))

    entry_trigger = (close > day_or_high * breakout_mult) & (~pd.Series(is_opening_bar, index=df.index))
    exit_trigger = close < day_or_low

    pos_arr = [0] * len(df)
    in_pos = False
    hold_hours = 0
    cur_day = None
    entry_arr = entry_trigger.fillna(False).to_numpy()
    exit_arr = exit_trigger.fillna(True).to_numpy()
    day_arr = df["_day"].to_numpy()

    for i in range(len(df)):
        if in_pos and day_arr[i] != cur_day:
            # day boundary -> flatten
            in_pos = False
            hold_hours = 0

        if in_pos:
            hold_hours += 1
            if exit_arr[i] or hold_hours >= max_hold_hours:
                in_pos = False
                hold_hours = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_hours = 0
                cur_day = day_arr[i]
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    breakout_mult: float = 1.0,
    max_hold_hours: int = 12,
) -> pd.Series:
    """Returns DAILY-compounded strategy returns (even though signals/data
    are hourly) so downstream validators (which hardcode freq='D'
    annualization -- see validation/validators.py check_sharpe_ratio) get a
    correctly-scaled Sharpe. Compounds intraday hourly position*return legs
    within each UTC calendar day into one daily return.
    """
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        breakout_mult=breakout_mult,
        max_hold_hours=max_hold_hours,
    )
    hourly_ret = df["close"].pct_change().fillna(0.0)
    strat_hourly_ret = position.shift(1).fillna(0) * hourly_ret
    daily_ret = (1.0 + strat_hourly_ret).groupby(df.index.normalize()).prod() - 1.0
    daily_ret.index = pd.to_datetime(daily_ret.index)
    return daily_ret
