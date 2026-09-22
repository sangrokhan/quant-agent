# Backtest Report: CMMA Mean Reversion (REJECTED)

**Strategy file:** `strategies/2026-09-23_cmma_meanrev.py`
**Date:** 2026-09-23

## Hypothesis

Source: Aligrithm "2.12 CMMA: A Better Momentum Primitive Than
Price-minus-MA Alone" (4 May 2026),
https://aligrithm.com/cmma-a-better-momentum-primitive-than-price-minus-ma-alone/
Fully disclosed formula:
`CMMA(k)_t = [ln(C_t) - mean(ln(C_{t-i}), i=1..k)] / [ATR_W(ln C)_t * sqrt(k+1)]`
(log prices, MA excludes current bar, ATR on log prices includes current
bar, sqrt(k+1) lookback-independence divisor).

This repo's adaptation: long when CMMA <= entry_threshold (deep
statistical deviation below trend, ATR-normalized), exit when CMMA
reverts >= exit_threshold (default 0) or a max_hold_days time-stop.

## Grid summary (Step 6)

`run_strategy_grid`, QQQ/SPY + BTC/USDT/ETH/USDT, k in {10,20,30},
entry_threshold in {-1.5,-2.0}, vol_regime_splits=3:

- **72 total cells, only 1 passed (pass_fraction = 0.014)**
- By asset class: equity 0/36, crypto 1/36
- By vol regime: low 0/24, mid 0/24, high 1/24
- Best cell: BTC/USDT, k=20, entry=-1.5, high-vol regime, Sharpe 1.004
  (barely above threshold, single cell)
- Worst cell: QQQ, k=10, entry=-2.0, high-vol, Sharpe -0.384

## Diagnostic

Because the sqrt(k+1)-normalized ATR-scaled construction is designed
(per source's own stated purpose) to be a *stationary ML feature*, not a
threshold-tuned trading oscillator, entry_threshold=-1.5/-2.0 std-equivalent
units is an extremely rare event: QQQ k=20/entry=-1.5 spends only ~1.0% of
days in a position (2 total trades over the full 2019-2026 sample), giving
essentially no statistical power for the mean-reversion edge to
manifest through vectorbt's Sharpe/MDD calc.

## Decision

**REJECTED.** Grid pass_fraction 0.014 (1/72) is a decisive failure — the
disclosed CMMA formula, as adapted into a threshold mean-reversion
oscillator, produces far too few trades at any of the tested
entry_threshold/k combinations to generate a usable edge. Full
single-config validator suite (Step 7) skipped given the decisive grid
failure, consistent with prior repo convention for pass_fraction < 0.1.
Strategy file kept as a record of a rejected attempt; not live.

**Note for future loops:** CMMA (the raw indicator, without the specific
threshold rule tested here) may still be worth revisiting with much looser
thresholds (e.g. -0.5 to -1.0) or as a continuous-signal/vol-targeted
overlay rather than a binary threshold-crossing entry, since the underlying
construction is well-motivated (log-price + ATR-scale + sqrt(k+1)
normalization) -- the rejection here is specifically about the naive
threshold-crossing adaptation, not necessarily the primitive itself.
