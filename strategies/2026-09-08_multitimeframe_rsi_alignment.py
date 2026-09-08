"""Strategy: Multi-Timeframe RSI alignment (daily > weekly > monthly).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-136):
Per https://medium.com/@FMZQuant/multi-timeframe-rsi-trading-strategy-169
cc2771848's disclosed rule (originally for 15m/1h/4h intraday timeframes,
adapted here to this repo's daily-bar universe using daily/weekly/monthly
resampled RSI as the timeframe ladder): a buy signal fires when the FASTER
timeframe's RSI is above the MEDIUM timeframe's RSI, which is above the
SLOWEST timeframe's RSI (RSI_daily > RSI_weekly > RSI_monthly), provided
the slowest RSI is above 30 (avoid buying into a structurally oversold
slow trend); exit when the fastest RSI crosses back below the medium RSI.

This is DISTINCT from Elder's Triple Screen (2026-09-04-044, rejected),
which uses a weekly MACD-Histogram SLOPE (not RSI) as its "tide" filter
gating a daily Stochastic %K pullback trigger (not an RSI-ordering
condition) -- here all three timeframes use the SAME indicator (RSI) and
the signal is a strict ORDERING/alignment across three RSI values, not a
slope-filter-gates-a-different-oscillator construction.

Signal logic
------------
- Daily RSI(14) computed directly on daily closes.
- Weekly RSI(14): resample closes to week-end (W-FRI), compute RSI(14) on
  that resampled series, then forward-fill back to daily frequency (a
  weekly value only updates once a week, avoiding look-ahead: the weekly
  bar's RSI is available starting the bar AFTER that week closes).
- Monthly RSI(14): identical construction at month-end (M) frequency.
- Long entry: RSI_daily > RSI_weekly > RSI_monthly (strict alignment) AND
  RSI_monthly > monthly_oversold_floor (default 30).
- Exit: RSI_daily crosses back below RSI_weekly (fastest loses its edge
  over medium, per the source's own stated exit rule).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def _resampled_rsi_ffill(close: pd.Series, freq: str, period: int) -> pd.Series:
    """Compute RSI on a resampled (e.g. weekly/monthly) close series, then
    forward-fill it back onto the original daily index, SHIFTED by one bar
    of the resampled series to avoid look-ahead (a week/month's RSI value
    only becomes known/usable the day after that period closes)."""
    resampled_close = close.resample(freq).last()
    resampled_rsi = _rsi(resampled_close, period)
    # Shift so a period's RSI is only visible starting the NEXT period.
    resampled_rsi_shifted = resampled_rsi.shift(1)
    # Reindex forward-filled onto the daily index: at each daily bar, use
    # the most recently COMPLETED period's RSI value.
    daily_index = close.index
    # Build a series aligned to resampled period end-dates, then reindex.
    aligned = resampled_rsi_shifted.reindex(
        pd.DatetimeIndex(resampled_rsi_shifted.index).union(daily_index)
    ).sort_index().ffill()
    return aligned.reindex(daily_index)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    monthly_oversold_floor: float = 30.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi_daily = _rsi(close, rsi_period)
    rsi_weekly = _resampled_rsi_ffill(close, "W-FRI", rsi_period)
    rsi_monthly = _resampled_rsi_ffill(close, "ME", rsi_period)

    aligned = (rsi_daily > rsi_weekly) & (rsi_weekly > rsi_monthly)
    monthly_ok = rsi_monthly > monthly_oversold_floor
    entry = aligned & monthly_ok.fillna(False)

    exit_signal = rsi_daily < rsi_weekly

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
