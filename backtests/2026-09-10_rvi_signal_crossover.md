# Backtest Report: Relative Vigor Index (RVI) Signal Crossover

**Strategy file:** `strategies/2026-09-10_rvi_signal_crossover.py`
**Date:** 2026-09-10
**Outcome:** REJECTED

## Hypothesis

Per Investopedia's Relative Vigor Index guide
(https://www.investopedia.com/terms/r/relative_vigor_index.asp): the RVI
compares close-vs-open (numerator) to high-vs-low range (denominator), each
4-bar weighted-averaged (1,2,2,1) then SMA-smoothed over N periods,
calculated similarly to the Stochastic Oscillator but using close-vs-OPEN
rather than close-vs-LOW. Source's disclosed rule: RVI crossing above its
own signal line (a further 4-bar weighted average of RVI) is bullish; below
is bearish. First RVI strategy in this repo.

## Step 6 grid summary

Grid: `n_period` in {8, 10, 14} x `max_hold_days` in {10, 20} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (72 cells,
2018-01-01 to 2024-12-31).

- pass_fraction: 0.222 (16/72)
- by_asset_class: equity 16/36, crypto 0/36 (decisive crypto fail)
- by_vol_regime: low 11/24, mid 5/24, high 0/24
- Best cell: n_period=14, max_hold_days=10, SPY, low-vol tercile,
  Sharpe 2.05. n_period=10, max_hold_days=10 was also strong across
  multiple cells (QQQ low 1.88, mid 1.98; SPY low 1.28).

## Step 7 single-config validation (n_period=10, max_hold_days=10, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.591 | 0.035 | >= 1.0 | No / No |
| Max drawdown | 0.346 | 0.346 | <= 0.25 | No / No |
| TC survival (5bps/trade) | 0.406 | -0.151 | >= 0.5 | No / No |
| Walk-forward (4 splits) | 0.75 (3/4) | 0.50 (2/4) | >= 0.75 | Yes / No |
| Parameter sensitivity | 0.326 | 0.714 | <= 0.5 | Yes / No |

Trade counts (entries only): QQQ 156, SPY 162 over ~7 years — a very high
frequency (roughly one entry every ~11 trading days), similar to the
already-rejected Center of Gravity oscillator this same run.

## Decision: REJECTED

Decisive rejection on nearly every axis: full-sample Sharpe misses badly on
both symbols (QQQ 0.591, SPY effectively zero at 0.035), max drawdown
breaches the 25% cap on both (34.6%/34.6%), transaction-cost survival fails
outright given the very high trade frequency (156-162 entries/7yr), and SPY
additionally fails walk-forward and parameter sensitivity. The
tercile-conditioned grid's promising low-vol cells (Sharpe 1.3-2.1) do not
remotely survive full-sample validation. Consistent with this run's earlier
finding (Center of Gravity oscillator) that fast, sensitive crossover
oscillators trade too frequently on daily bars to survive realistic costs;
RVI compounds this with a worse drawdown profile.

## Source

- https://www.investopedia.com/terms/r/relative_vigor_index.asp
