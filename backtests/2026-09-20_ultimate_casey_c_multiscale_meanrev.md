# Ultimate Casey C% Multi-Timescale Mean Reversion — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_ultimate_casey_c_multiscale_meanrev.py`
**Source(s):**
- https://statoasis.com/overfit/research/ultimate-c-a-smarter-mean-reversion-indicator-for-beginner-traders (Ali Casey, StatOasis)
- https://strategyquant.com/codebase/ultimate-casey-c/ (indicator construction detail: short/medium/long ROC percentile ranks, weighted + smoothed)

## Hypothesis

Combining three ROC-based percentile-rank ("CaseyC%") lookback horizons
(short weighted most, medium, long weighted least) into a single smoothed
oscillator ("Ultimate C%") produces more reliable oversold/overbought
mean-reversion signals than a single-lookback CaseyC%/RSI construction.
Long entry when UltimateC crosses below `entry_level` (oversold); exit when
it crosses back above `exit_level` or after `max_hold_days` (time-stop added
by this repo).

## Grid test summary (Step 6)

288 cells: `lookback∈{5,8} × entry_level∈{20,25,30} × exit_level∈{65,75} ×
max_hold_days∈{7,10}` on equity {QQQ, SPY} and crypto {BTC/USDT, ETH/USDT},
3 vol-regime terciles, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.174** (50/288 cells passed Sharpe≥1.0)
- **by_asset_class:** equity 50/144 passed; **crypto 0/144 passed (decisive fail)**
- **by_vol_regime:** low 39/96, mid 1/96, high 10/96 — signal edge concentrated almost entirely in low-vol regime
- **best_cell:** lookback=5, entry_level=30, exit_level=65, max_hold_days=7, SPY, low-vol regime, Sharpe 2.98
- **worst_cell:** lookback=8, entry_level=25, exit_level=65, max_hold_days=7, QQQ, mid-vol regime, Sharpe -0.67

## Single-config validation (Step 7) — best_cell params on SPY, full sample 2019-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.588 | ≥1.0 |
| Max drawdown | pass | 18.0% | ≤25% |
| Transaction cost survival (5bps/trade, 77 trades) | pass | 0.535 | ≥0.5 |
| Walk-forward (4 splits) | **FAIL** | 0.50 (2/4 splits positive) | ≥0.75 |
| Parameter sensitivity (entry_level 20/25/30) | pass | rel_std 0.180 | ≤0.5 |

## Interpretation

The grid's "best cell" Sharpe of 2.98 is a **low-vol-regime-tercile-only**
figure — restricted to roughly 1/3 of the sample. Full-sample (all regimes,
no low-vol gate) Sharpe collapses to 0.588, and walk-forward only holds in
2 of 4 splits. This matches the pattern already seen with several prior
StatOasis-derived single-lookback CaseyC% variants (2026-09-20-133,
2026-09-20-134): the raw crossover-threshold rule works only in low-vol
sub-periods and needs an explicit vol-regime gate to be viable, which this
iteration did not add (out of scope for time budget this iteration).

## Decision: **REJECTED**

Full-sample Sharpe (0.588) and walk-forward (0.50) both fail against
standard thresholds. Crypto asset class decisively fails (0/144 grid
cells). A future iteration could revisit this exact indicator construction
with an added low-vol realized-vol regime gate (as done successfully for
2026-09-20-140 RSI(2)+ATR%) — noted as a candidate rescue attempt, not
executed this iteration.
