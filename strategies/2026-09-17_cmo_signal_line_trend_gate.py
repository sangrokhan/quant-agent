"""Strategy: Chande Momentum Oscillator (CMO) signal-line crossover with
SMA200 trend gate and a fixed short max-hold time-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, this iteration):
Per QuantifiedStrategies.com "Chande Momentum Oscillator Trading Strategy --
Setup, Trading Rules And Backtest"
(https://www.quantifiedstrategies.com/chande-momentum-oscillator-trading-strategy/,
read this iteration via browser_exec after web_search DDGS backend returned
a "search-only, cannot extract" error for web_extract on this URL). The
source discloses:
  - CMO formula: 100 * (SHc - SLc) / (SHc + SLc), SHc/SLc = sum of
    higher/lower closes over n periods (n=9, "the most used timeframe" per
    source, and the period used in their own SPY backtest).
  - Oversold/overbought at -50/+50; zero-line and signal-line (9-period MA
    of CMO) crossovers are the source's own disclosed generic entry
    triggers ("when the indicator crosses above the signal line, they
    consider it a bullish signal").
  - Source's own backtest finding (SPY, dividend-adjusted): "we put a 5-day
    maximum holding period because we noted that it worked pretty well...
    as we increased the holding period to 10, 15, and 30 days, the returns
    of the strategy decreased" -- i.e. a short, ~5-day fixed hold is the
    source's own empirically-preferred exit, not an arbitrary choice made
    here.

This iteration operationalizes the source's disclosed signal-line-crossover
entry + short fixed-hold exit (the specific numeric rules given in the
article's body were not fully re-transcribed beyond the above, since the
article's own itemized "Trading Rules" list sits behind an unrendered
dynamic block on the page) as a concrete, testable long-only rule:
  - Trend filter: close > SMA(trend_window=200) (source implies momentum
    signals are only reliable "in the direction of the trend").
  - CMO(cmo_len=9) computed from daily closes.
  - Signal line = SMA(CMO, signal_len=9) per source's own disclosed
    "9-period moving average... as a signal line".
  - Entry: CMO crosses above its signal line while CMO < 0 (i.e. the
    crossover happens from a momentum-trough / early-recovery zone, closer
    to the source's -50 oversold framing than a random mid-range whipsaw
    cross) AND trend filter is up.
  - Exit: max_hold_days (default 5, per source's own disclosed backtest
    finding) time-stop, or CMO crossing back below its signal line,
    whichever comes first.

First Chande Momentum Oscillator strategy in this repo -- distinct from
every RSI/CRSI/RMI/Stochastic/CCI oscillator-family entry already tested:
CMO uses a raw (SHc-SLc)/(SHc+SLc) construction (not a ratio-of-averages
like RSI, nor a range-position ratio like Stochastic/CCI), and this
iteration's trigger (signal-line crossover from below-zero, gated by
trend, exited on a short fixed hold) is a novel combination for this repo.

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


def _cmo(close: pd.Series, cmo_len: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    sum_up = up.rolling(cmo_len, min_periods=cmo_len).sum()
    sum_down = down.rolling(cmo_len, min_periods=cmo_len).sum()
    denom = (sum_up + sum_down).replace(0, pd.NA)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cmo_len: int = 9,
    signal_len: int = 9,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    trend_up = (close > sma_trend).fillna(False)

    cmo = _cmo(close, cmo_len)
    signal = cmo.rolling(signal_len, min_periods=signal_len).mean()

    cross_up = (cmo > signal) & (cmo.shift(1) <= signal.shift(1)) & (cmo < 0)
    cross_down = (cmo < signal) & (cmo.shift(1) >= signal.shift(1))
    cross_up = cross_up.fillna(False)
    cross_down = cross_down.fillna(False)

    pos = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_pos = False
            else:
                pos.iloc[i] = 1
        else:
            if bool(trend_up.iloc[i]) and bool(cross_up.iloc[i]):
                in_pos = True
                entry_idx = i
                pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cmo_len: int = 9,
    signal_len: int = 9,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return daily strategy returns (position lagged 1 day to avoid look-ahead)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        trend_window=trend_window,
        cmo_len=cmo_len,
        signal_len=signal_len,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
