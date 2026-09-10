"""Strategy: Connors/Alvarez VIX RSI + VIX gap-up confirmation (TuringTrader rule).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-018):
Direct fix attempt for this repo's near-miss `2026-09-05-052` (Connors/
Alvarez VIX RSI, full-period Sharpe below threshold on both QQQ (0.654)
and SPY (0.829) despite every other validator passing cleanly; low trade
count 39-41 over 7.5y suggested a real but too-infrequent/low-magnitude
edge).

Per https://www.turingtrader.com/portfolios/connors-vix-rsi/ (visited this
iteration), TuringTrader's own restatement of Connors & Alvarez's exact
published rule (from "Short Term Trading Strategies That Work", 2009)
includes a FOURTH condition that this repo's original 2026-09-05-052
implementation omitted: "today's VIX open is greater than yesterday's
close" -- i.e. the VIX must GAP UP intraday on the signal day, not merely
have a high RSI(2) reading. This tightens selectivity toward genuine
single-day fear spikes (an overnight/opening gap up in fear) rather than
any day where a 2-bar RSI happens to be elevated, which may better isolate
the "acute, still-fresh" spikes the strategy is designed to fade.

Full rule (per TuringTrader):
1. Tradable-asset close > its own 200-day SMA (uptrend filter).
2. RSI(2) of the tradable asset's close < `price_rsi_entry` (30).
3. RSI(2) of the VIX's own close series > `vix_rsi_entry` (90).
4. NEW: today's VIX open > yesterday's VIX close (VIX gapped up).
Exit: RSI(2) of the tradable asset > `price_rsi_exit` (65), or a
`max_hold_days` time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import sys
import os
from datetime import timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.DataFrame:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    vix = load_equity("^VIX", start, end)
    return _prep(vix)


def _rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    price_rsi_entry: float = 30.0,
    vix_rsi_entry: float = 90.0,
    price_rsi_exit: float = 65.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series on the TRADABLE asset."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    price_rsi2 = _rsi(close, period=2)

    vix = _fetch_vix(df.index)
    vix_close = vix["close"].reindex(df.index).ffill()
    vix_open = vix["open"].reindex(df.index).ffill() if "open" in vix.columns else vix_close
    vix_rsi2 = _rsi(vix["close"], period=2).reindex(df.index).ffill()
    vix_gap_up = vix_open > vix_close.shift(1)

    uptrend = close > sma_trend
    entry_signal = (
        uptrend
        & (price_rsi2 < price_rsi_entry)
        & (vix_rsi2 > vix_rsi_entry)
        & vix_gap_up.fillna(False)
    ).fillna(False)
    exit_signal = (price_rsi2 > price_rsi_exit).fillna(False)

    valid = sma_trend.notna() & price_rsi2.notna() & vix_rsi2.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
