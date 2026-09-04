"""Strategy: Woodie's CCI Zero Line Reject (ZLR), long-only trend-continuation
pullback entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-007):
Woodie's CCI trading system (per TrendSpider's aggregated guide) treats an
established trend as CCI staying on one side of the zero line for
trend_established_bars or more consecutive bars. Its signature "Zero Line
Reject" (ZLR) pattern -- described as the workhorse trade, "a momentum
pullback entry: it buys resumption of an established trend rather than
picking tops or bottoms" -- occurs when CCI, having stayed positive for an
established uptrend, dips down toward (but does NOT cross below) the zero
line, then bounces back upward without ever going negative. This is tested
here as a long-only mechanical proxy: after an established positive-CCI
trend, CCI dips into a tolerance band just above zero (0 to reject_band)
and then closes back above the tolerance band without ever printing a
negative value in between -- entering long on that bounce. Exit when CCI
crosses below zero (trend genuinely broken) or a max_hold_days time-stop.
Distinct from the two already-tested CCI strategies in this repo: the
oversold-mean-reversion CCI<-90 dip-buy (2026-09-04-024, opposite economic
thesis -- buying deep oversold rather than a shallow pullback within an
existing uptrend) and the CCI>+100 breakout-momentum entry (2026-09-04-072,
which requires CCI to newly cross +100, not merely stay positive and dip
toward zero).

Signal logic
------------
- CCI(cci_window) via Lambert's original mean-absolute-deviation
  formulation (typical price vs its rolling mean, scaled by 0.015).
- Trend established (bullish): CCI has stayed > 0 for the trailing
  trend_established_bars bars.
- ZLR reject zone: CCI dips into (0, reject_band] without going <= 0.
- Entry (long): CCI was in the reject zone on the prior bar and closes back
  above reject_band on the current bar, with the established-trend
  condition true.
- Exit: CCI crosses below 0 (trend broken), OR a max_hold_days time-stop.
- Flat otherwise.

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


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(window).mean()
    mad = typical_price.rolling(window).apply(
        lambda x: abs(x - x.mean()).mean(), raw=True
    )
    cci = (typical_price - sma_tp) / (0.015 * mad.replace(0.0, pd.NA))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 14,
    trend_established_bars: int = 6,
    reject_band: float = 30.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    cci = _cci(df, cci_window)

    cci_positive = cci > 0
    trend_established = cci_positive.rolling(trend_established_bars).sum() >= trend_established_bars

    in_reject_zone = (cci > 0) & (cci <= reject_band)
    bounced_up = (cci > reject_band) & in_reject_zone.shift(1).fillna(False)

    entry = bounced_up & trend_established.fillna(False)
    exit_signal = cci <= 0

    position = pd.Series(0, index=cci.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(cci)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
