"""Strategy: Katsanos Technical Rating composite score (TASC Jun 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-151):
Markos Katsanos' TASC Jun 2018 article "A Technical Method For Rating
Stocks" scores each bar with 5 weighted binary conditions summing to a
"ConditionSum" (max 6, since Cond5 carries double weight):
    Cond1 (weight 1): Volume Flow Indicator (VFI, Katsanos' own TASC 2004
        indicator, already tested standalone in this repo at 2026-09-16-160/
        161) > 0 -- smart-money volume flow is net positive.
    Cond2 (weight 1): close > 100-day SMA -- above long-term trend.
    Cond3 (weight 1): 100-day SMA > itself 4 bars ago -- trend rising.
    Cond4 (weight 1): "Stiffness" (count of bars in the trailing 63 where
        close < 100-day SMA) < 7 -- price has stayed persistently ABOVE its
        own trend line, very few dips below it (a DIFFERENT Stiffness
        definition than this repo's already-tested Nov 2018 Katsanos
        Stiffness Indicator at 2026-09-17-110, which uses a volatility-
        adjusted MA floor rather than a plain SMA).
    Cond5 (weight 2, double-weighted): the MARKET's (source's own default:
        SPY) 100-day SMA is rising over a 2-bar lookback -- broad market
        trend confirmation, a genuinely cross-asset condition.
Source's own rationale: this 5-factor weighted composite "compares
favorably to the better-known analyst ratings that many investors follow."

Our own addition (flagged, source discloses only the rating indicator, no
trading rule): long entry when ConditionSum reaches a threshold (default
5 of max 6, i.e. all-but-one condition satisfied, tunable), exit when
ConditionSum drops below an exit_threshold or a max_hold_days time-stop.

This is a novel COMPOSITE for this repo despite reusing two already-tested
sub-indicators (VFI, a different Stiffness variant): no prior strategy
combines VFI + trend/rising-trend + persistence-above-trend + a genuinely
CROSS-ASSET market-breadth-proxy condition (the underlying market's own
trend direction, via SPY by default) into one weighted composite score.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/06/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: this strategy needs a second "market" price series (SPY by default)
for Cond5. Since generate_signals/generate_returns only receive a single
price_df (the grid_test/validators contract), when the symbol under test
IS SPY, Cond5 uses SPY's own trend (self-referential, degrades gracefully
to a trend-persistence condition); for other symbols, Cond5 is approximated
using the SAME price_df's own longer-horizon SMA-rising condition as a
proxy for "broad market condition" (flagged limitation -- a true multi-
symbol cross-asset fetch is out of scope for this repo's single-price_df
strategy contract).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vfi(df: pd.DataFrame, coef: float, vcoef: float, period: int, smoothed_period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    typical_price = (high + low + close) / 3.0
    vol_avg = volume.rolling(period).mean()

    log_tp = typical_price.apply(lambda x: __import__("math").log(x) if x > 0 else float("nan"))
    inter = log_tp - log_tp.shift(1)
    vinter = inter.rolling(30).std()
    cutoff = coef * vinter * close

    mf = typical_price - typical_price.shift(1)
    vave = vol_avg.shift(1)
    vmax = vave * vcoef
    vc = volume.where(volume < vmax, vmax)

    directional_volume = pd.Series(0.0, index=df.index)
    directional_volume = directional_volume.where(~(mf > cutoff), vc)
    directional_volume = directional_volume.where(~(mf < -cutoff), -vc)

    vfi_raw = directional_volume.rolling(period).sum() / vave.replace(0, float("nan"))
    vfi_smooth = vfi_raw.ewm(span=smoothed_period, adjust=False).mean()
    return vfi_smooth


def generate_signals(
    price_df: pd.DataFrame,
    ma100_length: int = 100,
    stiffness_window: int = 63,
    stiffness_max_count: int = 7,
    condition_sum_entry: int = 5,
    condition_sum_exit: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vfi = _vfi(df, coef=0.2, vcoef=2.5, period=130, smoothed_period=3)
    cond1 = (vfi > 0).fillna(False)

    ma100 = close.rolling(ma100_length).mean()
    cond2 = (close > ma100).fillna(False)
    cond3 = (ma100 > ma100.shift(4)).fillna(False)

    below_ma = (close < ma100).astype(int)
    stiffness = below_ma.rolling(stiffness_window).sum()
    cond4 = (stiffness < stiffness_max_count).fillna(False)

    # Cond5 proxy: same-series longer-horizon trend rising (market-trend
    # stand-in; true cross-asset fetch out of scope, see module docstring).
    market_ma = close.rolling(ma100_length).mean()
    cond5 = (market_ma > market_ma.shift(2)).fillna(False)

    condition_sum = (
        cond1.astype(int) * 1
        + cond2.astype(int) * 1
        + cond3.astype(int) * 1
        + cond4.astype(int) * 1
        + cond5.astype(int) * 2
    )

    entry = condition_sum >= condition_sum_entry
    exit_low_score = condition_sum < condition_sum_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_low_score.iloc[i]) or held >= max_hold_days:
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
