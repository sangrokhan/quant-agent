# Backtest Report: Donchian Breakout + Bulkowski MA-Position Filter

**Strategy file:** `strategies/2026-09-22_donchian_breakout_bulkowski_ma_filter.py`
**Date:** 2026-09-22
**Outcome:** REJECTED (full-sample Sharpe fails on primary config)

## Hypothesis

Source: Bulkowski's Moving Average Study
(https://thepatternsite.com/MovingAvgs.html, read via browser_exec this
iteration; 21,696 sample chart-pattern trades, 1989-2009). Source's
disclosed finding: an UPWARD chart-pattern breakout performs better
(larger avg move, lower failure rate) when the close the day BEFORE the
breakout was BELOW the 9-day SMA, vs. above it (26.2-28.4% avg move &
29.7-32.7% fail rate vs. 26.5%/32.2% unconditional benchmark).

Adapted mechanically: define "breakout" as a Donchian N-day-high break
(no chart-pattern classifier available on OHLCV-only data). Long entry
requires (1) close > rolling N-day high (breakout), (2) yesterday's close
< 9-day SMA (Bulkowski's "more favorable" pre-breakout state), (3) close >
SMA(200) uptrend gate (added, not in source). Exit on close < Donchian low
(support break) or `max_hold_days` time-stop.

## Primary config (QQQ, donchian_window=20, ma_filter_window=9, max_hold_days=40)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.957 | >= 1.0 |
| Max drawdown | pass | 7.9% | <= 25% |
| TC survival (net Sharpe, 10bps/trade) | pass | 0.927 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (rel. std) | pass | 0.413 | <= 0.5 |

Number of trades: 10 (full sample 2016-06 to 2026-09).

## Step 6 grid summary (144 cells: donchian_window in [20,40,55] x
ma_filter_window in [9,5] x max_hold_days in [20,40] x {QQQ,SPY,BTC/USDT,ETH/USDT}
x low/mid/high vol tercile)

- Overall pass_fraction: 0.160 (23/144)
- By asset class: equity 21/72 passed; crypto 2/72 passed
- By vol regime: low 21/48; mid 2/48; high 0/48 -- strategy only works in
  low realized-vol regimes and essentially never in high-vol regimes,
  consistent with a mean-reversion-flavored breakout-after-dip construction.
- Best cell: QQQ, donchian_window=20/ma_filter_window=9/max_hold_days=40,
  low-vol regime, Sharpe 2.12
- Worst cell: SPY, donchian_window=55/ma_filter_window=5/max_hold_days=20,
  high-vol regime, Sharpe -1.35

## Decision

REJECTED. The grid shows the strategy is real but narrow (only low-vol
equity slices clear the Sharpe bar), and critically the single best
full-sample config on QQQ (the strongest symbol in the grid) still falls
short of the 1.0 Sharpe threshold (0.957) despite passing every other
validator (MDD, TC survival, walk-forward, parameter sensitivity). This
is a genuine near-miss, not a decisive rejection -- a future iteration
could revisit with a low-vol-regime gate added directly to the entry
condition (restricting trading to the regime where the grid shows it
actually works) as a rescue attempt.
