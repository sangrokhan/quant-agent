"""Strategy: Single-line VWMA (Volume-Weighted Moving Average) mean-reversion
crossunder/crossover, per QuantifiedStrategies.com's own disclosed
"Strategy 1" VWAP-moving-average backtest.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-003):
Per https://www.quantifiedstrategies.com/vwap-trading-strategy/ ("VWAP
Trading Strategy (Backtest)"), the source's own disclosed "Strategy 1" rule
on SPY: "When the close of SPY crosses BELOW the N-day VWAP moving average,
we buy SPY at the close. We sell when SPY's close crosses ABOVE the same
average." The source's own results table (CAGR by N-day period 5/10/25/
50/100/200) shows short periods (5-day) work best for this mean-reversion
framing (CAGR 8.18% at N=5 vs 2.67-2.93% at N=100-200), i.e. this is a
SHORT-period, single-line mean-reversion strategy -- explicitly the
opposite framing from Strategy 2 (long-period trend-following crossover,
which is essentially what this repo's existing dual VWMA crossover id
2026-09-04-060 already captures, but with TWO VWMA lines, not one crossed
against price).

This strategy is distinct from every prior VWAP/VWMA entry in this repo:
- 2026-09-04-060 (accepted, dual fast/slow VWMA crossover -- two VWMA
  lines, momentum framing)
- Anchored VWAP crossover variants (rolling-swing-low re-anchored, ATR-stop
  augmented -- different anchor mechanism entirely)
- VWAP band mean-reversion (volume-weighted stdev bands, not a plain single
  VWMA line)
- VWAP trend-continuation pullback (long-period rising-VWAP dip-buy)

Here: ONE VWMA line, price crosses BELOW it -> buy (mean-reversion long),
price crosses back ABOVE it -> sell -- the source's own exact disclosed
"Strategy 1" rule, short N-day period per the source's own best-performing
setting.

Signal logic
------------
- VWMA(N) = rolling N-day sum(close*volume) / sum(volume).
- Long entry: close crosses from >= VWMA to < VWMA (close below VWMA).
- Exit (flat): close crosses back above VWMA, or a max_hold_days time-stop
  (added robustness stop, not in the source's own bare rule, to avoid
  indefinite holds through a persistent downtrend).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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
    vwma_window: int = 5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series: single-line VWMA
    mean-reversion crossunder/crossover per QuantifiedStrategies.com's own
    disclosed 'Strategy 1' rule."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    pv = (close * volume).rolling(vwma_window).sum()
    vsum = volume.rolling(vwma_window).sum()
    vwma = pv / vsum.replace(0, pd.NA)

    below_vwma = (close < vwma).fillna(False)
    entry = below_vwma & ~below_vwma.shift(1).fillna(False)
    exit_meanrev = (close > vwma).fillna(False) & ~(close > vwma).shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
