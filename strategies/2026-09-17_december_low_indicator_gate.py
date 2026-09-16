"""Strategy: December Low Indicator (DLI, Lucien Hooper, 1970s) risk-off
gate on an SMA trend-following signal.

Hypothesis (this cron trigger's iteration 10):
Per Lucien Hooper's December Low Indicator (confirmed via Google SERP +
direct blog read this iteration, https://time-price-research-astrofin.
blogspot.com/2026/03/us-stock-indexes-trigger-rare-march.html, a March
2026 Jeffrey Hirsch commentary explicitly restating Hooper's original
1970s rule): "based on the Dow closing below its December closing low in
the first quarter of the New Year." Source's own disclosed historical
finding: "when the market has closed below its December closing low in
the first quarter of the year, the market has dropped, on average,
another 13.5% on the S&P 500 ... from the trigger point" -- i.e. a DLI
trigger is a bearish/risk-off signal that historically preceded further
declines. Operationalized as a regime gate on a primary SMA(trend_window)
trend-following signal: track each calendar year's prior-December closing
low; if price closes below that level at any point during Q1 (Jan-Mar) of
the current year, flip to a risk-off state (flat) for the remainder of
that DLI-check window (window_end_month, default April per the source's
"first quarter" framing, extendable), resetting each new year. This is a
GENUINELY NEW calendar-anomaly family for this repo (0 prior December Low
Indicator entries), distinct from the already-tested Turn-of-Month/
Santa-Claus-Rally/Presidential-Cycle/Pre-FOMC-Drift calendar strategies
(none of which reference a prior-year reference price level).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dli_risk_off(close: pd.Series, check_end_month: int) -> pd.Series:
    """For each year Y, find December(Y-1)'s closing low. During
    Jan-check_end_month of year Y, if close ever drops below that level,
    flag risk-off for the REMAINDER of that Jan-check_end_month window
    (source's own framing: a Q1 trigger signals further downside risk for
    that stretch of the year). Outside the check window, or once no
    trigger has fired, risk_off=False."""
    idx = close.index
    years = idx.year
    months = idx.month

    dec_low_by_year = {}
    for y in sorted(set(years)):
        dec_mask = (years == y) & (months == 12)
        if dec_mask.any():
            dec_low_by_year[y + 1] = close[dec_mask].min()

    risk_off = np.zeros(len(close), dtype=bool)
    triggered_this_year = {}
    c = close.to_numpy()
    for i in range(len(c)):
        y = years[i]
        m = months[i]
        if m <= check_end_month:
            dec_low = dec_low_by_year.get(y)
            if dec_low is not None:
                if triggered_this_year.get(y, False) or c[i] < dec_low:
                    triggered_this_year[y] = True
                    risk_off[i] = True
    return pd.Series(risk_off, index=idx)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    check_end_month: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend-following,
    gated flat whenever the December Low Indicator has triggered risk-off
    for the current year's Jan-check_end_month window."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    risk_off = _dli_risk_off(close, check_end_month)

    position = (trend_long.fillna(False) & ~risk_off).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    check_end_month: int = 4,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, check_end_month=check_end_month
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
