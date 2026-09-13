"""Strategy: Monthly-evaluated moving-average trend-following, REIT-sector
(XLRE/IYR) adaptation, also tested on crypto for asset-class breadth.

Source: Quantpedia blog "Anomaly-Based Trading Strategies in the Real Estate
Sector. Can the Market Be Beaten?" (16 March 2026, by Sona Beluska, read this
iteration via browser_exec -- https://quantpedia.com/anomaly-based-trading-strategies-in-the-real-estate-sector-can-the-market-be-beaten/).
Using the RlEst Fama-French real-estate industry index (1926-2025, monthly),
the study's own disclosed methodology: at the end of each month, compare the
index's current value to its N-month moving average; if current > MA,
invest in RlEst for the FOLLOWING month, else hold cash. Tested N in
[3..12] months; all N outperformed RlEst buy-and-hold (Sharpe/Calmar up to
3x higher) but underperformed the broader 12-industry market benchmark. No
prior REIT/real-estate MA-trend entry in this repo's knowledge base (one
prior REIT entry, 2026-09-12-203, tested a Bollinger+Donchian dual-entry
system on VNQ -- a different mechanism family; this is a plain monthly MA
trend rule, distinct).

Adaptation notes
-----------------
This repo's loaders provide DAILY OHLCV, not the source's native monthly
Fama-French index. This adaptation:
  - Uses XLRE (Real Estate Select Sector SPDR, since 2015) and IYR (iShares
    US Real Estate, since 2000) as REIT-sector-proxy equities, plus BTC/ETH
    for asset-class breadth (crypto obviously isn't a REIT, but the
    MECHANISM under test -- monthly-decision MA trend timing sized in
    trading days -- is asset-agnostic and this repo's grid-test harness
    requires an equity + crypto split).
  - Approximates the source's month-end evaluation via an
    eval_frequency_days parameter (default 21 trading days ~ 1 calendar
    month): the position is only allowed to CHANGE on evaluation days,
    holding flat/long for the entire following period otherwise (mirrors
    "invest for the following month" from the source, rather than
    re-evaluating and flipping every single day).
  - ma_window is expressed in trading days (ma_window=63 ~= 3 months,
    ma_window=252 ~= 12 months) to span the source's tested 3-12 month
    range.

Signal logic
------------
- On each evaluation day (every eval_frequency_days trading days), compute
  close vs its trailing ma_window-day SMA.
  - If close > SMA: go/stay long for the next eval_frequency_days days.
  - Else: go/stay flat (cash) for the next eval_frequency_days days.
- No intra-period changes (matches the source's monthly-decision design).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily returns)
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
    ma_window: int = 126,
    eval_frequency_days: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series, decided only on
    evaluation days (every eval_frequency_days trading days) and held
    constant in between (mirrors the source's monthly-decision design)."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(ma_window).mean()
    raw_signal = (close > sma).astype(int)

    position = pd.Series(0, index=close.index, dtype=int)
    current_pos = 0
    for i in range(len(close)):
        if i % eval_frequency_days == 0 and not pd.isna(sma.iloc[i]):
            current_pos = int(raw_signal.iloc[i])
        position.iloc[i] = current_pos
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's decision determines today's
    # return exposure (avoid look-ahead bias).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
