"""Strategy: RSI(3) + IBS dual-oversold mean-reversion in confirmed uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-082):
Per a Google AI-overview synthesis of QuantifiedStrategies.com's "RSI
Trading Strategy for Nasdaq Stocks (Only 17% Drawdown)" (browser_exec
fallback -- web_search DDGS backend returns mangled non-English results
this iteration; the direct article page was previously found paywalled in
2026-09-20-072 this same cron trigger, but the AI-overview now discloses
the exact numeric rule), the disclosed entry requires ALL of:
    1. Close > 200-day SMA (broad uptrend confirmed)
    2. 3-day RSI < 20 (short-term oversold)
    3. IBS = (Close - Low) / (High - Low) < 0.3 (closed near the day's
       low -- confirms the oversold reading isn't just a gap-down that
       recovered intraday)
The source's own liquidity/price filters (50-day avg volume > 10M shares,
price > $25, max 5 concurrent positions) are per-stock cross-sectional
constraints not applicable to this repo's single-symbol daily-bar
architecture (QQQ/SPY ETFs already satisfy liquidity/price trivially), so
they're omitted here. Exit rule not fully disclosed by the AI-overview;
this repo adapts the exit to IBS/RSI both recovering above their own
midpoints (IBS > 0.5 and RSI > 50), consistent with other IBS-mean-reversion
exits already validated in this repo (e.g. 2026-09-04-089's IBS>0.8 exit,
loosened here since we're adding a second RSI condition on entry that the
prior single-IBS strategies didn't have). This is a novel DUAL-OVERSOLD
AND-gate combo (13 prior IBS entries in this repo, none combine IBS with a
simultaneous RSI threshold).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int = 3) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    rsi_threshold: float = 20.0,
    ibs_threshold: float = 0.3,
    trend_window: int = 200,
    exit_ibs_threshold: float = 0.5,
    exit_rsi_threshold: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: close > SMA(trend_window) AND RSI(rsi_period) < rsi_threshold
    AND IBS < ibs_threshold. Exit: IBS > exit_ibs_threshold AND
    RSI(rsi_period) > exit_rsi_threshold (both conditions must recover,
    confirming reversion is complete).
    """
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    rsi = _rsi(close, period=rsi_period)
    ibs = (close - low) / (high - low).replace(0, pd.NA)
    trend_sma = close.rolling(trend_window).mean()

    entry = (close > trend_sma) & (rsi < rsi_threshold) & (ibs < ibs_threshold)
    exit_signal = (ibs > exit_ibs_threshold) & (rsi > exit_rsi_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.fillna(False).values
    exit_vals = exit_signal.fillna(False).values

    for i in range(len(close)):
        if in_position:
            position.iloc[i] = 1
            if bool(exit_vals[i]):
                in_position = False
        else:
            if bool(entry_vals[i]):
                in_position = True
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
