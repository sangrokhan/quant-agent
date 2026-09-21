"""Strategy: SPY-style opening gap-down mean-reversion "fade the gap" fill trade.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-009):
Per QuantifiedStrategies.com's disclosed "personal twist" gap-fill rule
(https://www.quantifiedstrategies.com/gap-fill-trading-strategies/): if SPY
gaps down between gap_min (-0.6%) and gap_max (-0.15%) at the open (open
vs prior close), AND the prior day's Close Location Value
CLV=(close-low)/(high-low) is below clv_threshold (0.25, i.e. prior day
closed near its low -- a mean-reversion setup precondition), go long at
the open. Target = target_fraction (0.75) of the gap size (partial
fill back toward the prior close); exit at the target if touched
intraday, else exit at the close with no other stop. Source's own EOD
backtest (2010-2012): 110 fills, 98 winners, average 0.19%/fill.

Adapted here to this repo's daily-bar-only OHLCV pipeline (no intraday
data) as a same-day trade using each signal day's own open/high/low/close:
if the day's high touches the target price, assume the target fill;
otherwise exit at that day's close. This is a fundamentally different
"holding period" shape than this repo's other strategies (a single-day
intraday round-trip rather than a multi-day directional position), but
uses the same generate_signals/generate_returns interface -- position is
only ever "open" (1) transiently within the entry day itself for
accounting purposes; the realized return that day already captures the
full round-trip.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position, 1 on
        trade days, purely informational since generate_returns embeds the
        full intraday round-trip return on those days)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trade_mask_and_returns(
    df: pd.DataFrame,
    gap_min: float,
    gap_max: float,
    clv_threshold: float,
    target_fraction: float,
) -> tuple[pd.Series, pd.Series]:
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)
    prior_high = high.shift(1)
    prior_low = low.shift(1)

    gap_pct = (open_ / prior_close) - 1.0

    prior_range = (prior_high - prior_low).replace(0, float("nan"))
    prior_clv = (prior_close - prior_low) / prior_range

    trade_mask = (
        (gap_pct <= -gap_min) & (gap_pct >= -gap_max) & (prior_clv < clv_threshold)
    ).fillna(False)

    target_price = open_ * (1.0 + target_fraction * gap_pct.abs())
    target_hit = high >= target_price

    fill_ret = target_price / open_ - 1.0
    close_ret = close / open_ - 1.0
    trade_ret = target_hit.where(trade_mask, other=False)
    day_ret = pd.Series(0.0, index=df.index)
    day_ret = day_ret.where(~trade_mask, other=close_ret)
    day_ret = day_ret.where(~(trade_mask & target_hit), other=fill_ret)

    return trade_mask, day_ret


def generate_signals(
    price_df: pd.DataFrame,
    gap_min: float = 0.0015,
    gap_max: float = 0.006,
    clv_threshold: float = 0.25,
    target_fraction: float = 0.75,
) -> pd.Series:
    df = _prep(price_df)
    trade_mask, _ = _trade_mask_and_returns(
        df, gap_min=gap_min, gap_max=gap_max,
        clv_threshold=clv_threshold, target_fraction=target_fraction,
    )
    return trade_mask.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    gap_min: float = 0.0015,
    gap_max: float = 0.006,
    clv_threshold: float = 0.25,
    target_fraction: float = 0.75,
) -> pd.Series:
    df = _prep(price_df)
    _, day_ret = _trade_mask_and_returns(
        df, gap_min=gap_min, gap_max=gap_max,
        clv_threshold=clv_threshold, target_fraction=target_fraction,
    )
    return day_ret.fillna(0.0)
