"""Strategy: "One Percent A Week" TQQQ weekly snapback (base/March-2026 TASC
variant, NOT the adaptive-target variant already tested as 2026-09-12-145).

Source: TASC (Technical Analysis of Stocks & Commodities) March 2026
Traders' Tips, "A High-Probability Weekly Trading Strategy For TQQQ" /
"Trading Snapbacks In A Leveraged ETF", via TradingView script description
https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/
(visited 2026-09-13, see knowledge_base/visited_pages.jsonl).

Source's own disclosed rules (fully mechanical, base variant -- distinct
from the ADAPTIVE variant 2026-09-12-145 which enters at Monday's OPEN with
a fixed 1.5% stop / 7% target that scales up/down based on Monday's
close-to-open return and adds a Tuesday momentum-fade exit):

1. Track Monday's opening price each week.
2. Enter on a `dip_pct` (source: 1%) pullback from that Monday open via a
   limit buy (only fires if the week's low actually trades down to that
   level -- this is the key mechanical difference from 2026-09-12-145's
   Monday-open market entry: this strategy may not enter most weeks).
3. Once filled, set a take-profit at `target_pct` (source: 1%) above the
   fill price, active starting the NEXT bar after fill (source waits one
   day so occasional >1% weekly gains are possible).
4. Breakeven stop: while in a position, if a drawdown of `breakeven_dd_pct`
   (source: 0.5%) or more from the fill price is observed, immediately set
   a resting limit sell at the entry price (breakeven) -- i.e. once
   breakeven triggers, the position exits at entry price (0 return) the
   first subsequent bar its range touches back up to entry, or at latest
   the Friday hard stop.
5. Hard stop at Friday close (market-on-close) exits any position not
   already closed by target/breakeven.

Adapted from source's intraday 5-min execution to this repo's daily-bar OHLC
data: daily low is used to test the dip-entry limit fill and the breakeven
drawdown trigger; daily high is used to test the take-profit touch; the
week's close-to-close move approximates entry/exit-day P&L since exact
intrabar fill price isn't available with daily bars (consistent
simplification with 2026-09-12_tqqq_adaptive_weekly_momentum_exit.py).

This is a genuinely different construction from 2026-09-12-145: conditional
LIMIT-ORDER dip entry (may skip weeks entirely) vs unconditional Monday-open
market entry; single fixed 1%/1% target/no-loss-widening vs the adaptive
variant's momentum-scaled 7%/1.5% target/stop and Tuesday fade-exit.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


def generate_signals(
    price_df: pd.DataFrame,
    dip_pct: float = 0.01,
    target_pct: float = 0.01,
    breakeven_dd_pct: float = 0.005,
) -> pd.Series:
    """Return a {0,1} long/flat position series (1 = in an active weekly trade)."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    iso_week = pd.Series([d.isocalendar()[:2] for d in df.index], index=df.index)
    position = pd.Series(0, index=close.index, dtype=int)

    n = len(df)
    week_groups: dict = {}
    for i in range(n):
        week_groups.setdefault(iso_week.iloc[i], []).append(i)

    for _wk, idxs in week_groups.items():
        idxs = sorted(idxs)
        monday_i = idxs[0]
        monday_open = open_.iloc[monday_i]
        dip_price = monday_open * (1 - dip_pct)

        filled = False
        fill_i = None
        fill_price = None
        target_price = None
        breakeven_armed = False

        for pos_j, i in enumerate(idxs):
            if not filled:
                # Test whether this day's range touches the dip limit price.
                if low.iloc[i] <= dip_price:
                    filled = True
                    fill_i = i
                    fill_price = dip_price
                    target_price = fill_price * (1 + target_pct)
                    position.iloc[i] = 1
                    # Friday (last day of week) hard-exit even on fill day.
                    if pos_j == len(idxs) - 1:
                        filled = False  # trade opened and closed same bar (Friday-only fill)
                continue

            # In an active trade from a prior day this week.
            position.iloc[i] = 1
            is_last_day_of_week = pos_j == len(idxs) - 1

            dd = (fill_price - low.iloc[i]) / fill_price
            if dd >= breakeven_dd_pct:
                breakeven_armed = True

            hit_target = high.iloc[i] >= target_price
            hit_breakeven_exit = breakeven_armed and high.iloc[i] >= fill_price

            if hit_target or hit_breakeven_exit or is_last_day_of_week:
                filled = False  # trade closes this bar

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Entry-day return is captured as fill-price-to-close (limit fill,
    conservative approx using the dip price itself); subsequent in-trade
    days use close-to-close; the exit day's own close-to-close move is
    already included via the day being marked position==1 (consistent with
    2026-09-12_tqqq_adaptive_weekly_momentum_exit.py's convention).
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    low = df["low"]
    position = generate_signals(price_df, **kwargs)

    dip_pct = kwargs.get("dip_pct", 0.01)

    daily_ret = pd.Series(0.0, index=close.index)
    n = len(close)
    for i in range(n):
        if position.iloc[i] == 1:
            if i == 0 or position.iloc[i - 1] == 0:
                # entry day: filled intraday at the dip price, held to close.
                iso_week_today = close.index[i].isocalendar()[:2]
                monday_open = None
                # find this week's Monday open for the dip-fill price
                j = i
                while j >= 0 and close.index[j].isocalendar()[:2] == iso_week_today:
                    j -= 1
                monday_idx = j + 1
                monday_open = open_.iloc[monday_idx]
                fill_price = monday_open * (1 - dip_pct)
                daily_ret.iloc[i] = (close.iloc[i] - fill_price) / fill_price
            else:
                daily_ret.iloc[i] = (close.iloc[i] - close.iloc[i - 1]) / close.iloc[i - 1]
    return daily_ret
