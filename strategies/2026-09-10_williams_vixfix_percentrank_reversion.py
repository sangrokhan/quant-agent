"""Strategy: Williams VIX Fix (WVF) PercentRank capitulation-spike mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/williamsvixfix/ (Larry Williams,
2007): the Williams VIX Fix (WVF) is a synthetic, instrument-agnostic VIX
proxy, WVF = (Highest(Close, wvf_window) - Low) / Highest(Close, wvf_window)
* 100 -- it spikes when the current low undercuts the recent highest close by
a large margin (a fear/capitulation signature). The source's own disclosed
long strategy: enter long when WVF's own PercentRank over a short lookback
(rank_lookback, default 10) exceeds an extreme threshold (default 98, i.e.
WVF is in the top 2% of its own recent range -- a capitulation spike just
occurred), and exit on the very next close that's higher than the prior
close (source's own simple "any up-day" exit, backtested at 366 trades,
avg 0.44%/trade, profit factor 1.78 on the source's own sample). This
implementation follows the source's rule directly (no added trend filter,
since the strategy is explicitly a short-horizon capitulation-bounce play
that source itself tests unconditionally), with a max_hold_days backstop
added since the source's own exit could theoretically hold indefinitely in a
sustained downtrend with no up-day. First Williams VIX Fix strategy in this
repo -- distinct from every PercentRank-of-ROC/RSI-composite family
(Connors RSI 2026-09-04-113, David Varadi Oscillator 2026-09-08-035) since
here PercentRank is applied to a range-based volatility-spike measure, not a
momentum/RSI-style series.

Signal logic
------------
- WVF[t] = (Highest(Close, wvf_window)[t] - Low[t]) / Highest(Close, wvf_window)[t] * 100
- Entry (long): PercentRank(WVF, rank_lookback)[t] >= entry_percentile
  (source's own default: rank_lookback=10, entry_percentile=98).
- Exit: close[t] > close[t-1] (source's own simple "any up day" rule), OR a
  max_hold_days time-stop backstop (added safety net not in the source).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _percent_rank(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling percent-rank of the current value within its own trailing
    window (0-100 scale), matching the source's PercentRank convention."""

    def _rank_last(window: pd.Series) -> float:
        current = window.iloc[-1]
        return 100.0 * (window < current).sum() / (len(window) - 1) if len(window) > 1 else 50.0

    return series.rolling(lookback).apply(_rank_last, raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    wvf_window: int = 22,
    rank_lookback: int = 10,
    entry_percentile: float = 98.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    highest_close = close.rolling(wvf_window).max()
    wvf = (highest_close - low) / highest_close * 100.0

    wvf_rank = _percent_rank(wvf, rank_lookback)

    entry_signal = wvf_rank >= entry_percentile
    up_day = close > close.shift(1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = entry_signal.fillna(False).values
    up_day_vals = up_day.fillna(False).values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = up_day_vals[i] or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    wvf_window: int = 22,
    rank_lookback: int = 10,
    entry_percentile: float = 98.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        wvf_window=wvf_window,
        rank_lookback=rank_lookback,
        entry_percentile=entry_percentile,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
