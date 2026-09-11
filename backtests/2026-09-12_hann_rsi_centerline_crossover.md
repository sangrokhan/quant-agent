# Hann-Windowed RSI Centerline Crossover — Backtest Report

**Date:** 2026-09-12
**Strategy file:** `strategies/2026-09-12_hann_rsi_centerline_crossover.py`
**Source:** TASC January 2022 Traders' Tips (John Ehlers, "(Yet Another
Improved) RSI Enhanced With Hann Windowing"), via
https://www.tradingview.com/scripts/tasc/page-3/

## Hypothesis

Replace Wilder's IIR-smoothed closes-up/closes-down RSI averaging with a
Hann-window FIR filter, producing an oscillator in [-1,+1] with a 0.0
centerline. Long when hann_rsi crosses above 0, exit on cross back below 0
or a time-stop.

## Best config (from grid search)

`length=21, max_hold_days=45`

## Single-config validator results (2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | **0.739 (FAIL, thr 1.0)** | **27.7% (FAIL, thr 25%)** | 0.687 (pass, thr 0.5) | 3/4=0.75 (pass) | 0.289 (pass, thr 0.5) |
| SPY | **0.343 (FAIL, thr 1.0)** | 21.9% (pass, thr 25%) | **0.284 (FAIL, thr 0.5)** | 3/4=0.75 (pass) | 0.453 (pass, thr 0.5) |

Both symbols fail full-sample Sharpe (the grid's "best cell" was a
low-vol-tercile SPY slice, not representative of the full sample).

## Grid-test summary (2019-01-01 to 2026-09-01)

Grid: `length in {10, 14, 21} x max_hold_days in {20, 30, 45}`, symbols
`{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, vol_regime_splits=3. 108 total cells.

- Overall pass_fraction: 0.287 (31/108)
- By asset class: equity 31/54 passed; **crypto 0/54 passed (decisive reject)**
- By vol regime: low 18/36, mid 10/36, high 3/36
- Best cell: SPY, length=21/max_hold_days=45, low-vol, Sharpe 3.09
- Worst cell: SPY, length=21/max_hold_days=45, mid-vol, Sharpe -0.41 (same
  config as the best cell -- extreme vol-regime dependence)

## Decision: REJECT (both equity symbols fail full-sample Sharpe; crypto decisively rejected)

The grid's headline "best cell" is a single low-vol-tercile slice; the SAME
parameter config produces a strongly negative Sharpe in the mid-vol tercile,
and the full-sample validator run confirms neither QQQ nor SPY clears the
Sharpe bar unconditionally. This looks like a regime-dependent edge (works
in calm markets, fails otherwise) rather than a robust standalone signal --
a future iteration could retry with an explicit low-vol regime gate, but
that is not attempted here.
