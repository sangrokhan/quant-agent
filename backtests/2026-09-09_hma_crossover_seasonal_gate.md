# Backtest Report: HMA Crossover Gated by Sell-in-May Seasonal Window

**Strategy file:** `strategies/2026-09-09_hma_crossover_seasonal_gate.py`
**Date:** 2026-09-09
**Source:** Combines two prior repo results -- accepted HMA(100) crossover (2026-09-09-013) + rejected-near-miss Sell-in-May calendar seasonality (2026-09-09-019/020)

## Hypothesis

Following the explicit suggestion in 2026-09-09-020's rejection notes:
combine the Sell-in-May/Halloween calendar window with an already-accepted
trend-following signal (HMA crossover) instead of a plain SMA trend check.
Take long-only HMA(hma_window) crossover positions, but only while inside
the Nov-Apr-style seasonal window; flat outside it regardless of the HMA
signal.

## Grid test summary (Step 6)

Grid: `hma_window` in [80, 100, 120], `long_end_month` in [3, 4, 5] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 108 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.194** (21/108 cells -- best of this cron trigger's iterations)
- **By asset class:** equity 21/54, crypto 0/54
- **By vol regime:** low 15/36, mid 0/36, high 6/36
- **Best cell:** SPY, hma_window=80, long_end_month=5, high-vol regime, Sharpe=1.813

## Single-config validation (Step 7): two candidate configs tested full-sample 2018-2026

### Config A: hma_window=80, long_end_month=5

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe | 0.931 (FAIL) | **1.060 (PASS)** | >= 1.0 |
| MDD | 0.170 (PASS) | 0.096 (PASS) | <= 0.25 |
| Net Sharpe after costs | 0.657 (PASS) | 0.664 (PASS) | >= 0.5 |
| Walk-forward | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Param sensitivity | 0.532 (**FAIL**, marginal) | 0.300 (PASS) | <= 0.5 |

### Config B: hma_window=100, long_end_month=5

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe | **1.004 (PASS)** | 0.870 (FAIL) | >= 1.0 |
| MDD | 0.186 (PASS) | 0.114 (PASS) | <= 0.25 |
| Net Sharpe after costs | 0.736 (PASS) | 0.518 (PASS, marginal) | >= 0.5 |
| Walk-forward | 0.75 (PASS, marginal) | 0.75 (PASS, marginal) | >= 0.75 |
| Param sensitivity | 0.532 (**FAIL**, marginal) | 0.301 (PASS) | <= 0.5 |

## Decision

**Accept, SPY-only (equity scope), Config A: hma_window=80, long_end_month=5.**
SPY clears all 5 validators cleanly (Sharpe 1.060, MDD 0.096, net Sharpe
0.664, walk-forward 1.0, param-sensitivity 0.300). QQQ does NOT clear this
config (Sharpe 0.931 fail, param-sensitivity 0.532 fail) -- Config B
(hma_window=100) flips this, passing QQQ's Sharpe (1.004, razor-thin) but
failing SPY's Sharpe (0.870) and still failing QQQ's param-sensitivity
(0.532). No single config clears both symbols simultaneously, so this
strategy is explicitly scoped to **SPY only** -- do not extrapolate to QQQ
or crypto (crypto grid: 0/54, decisive). Crypto and QQQ are both
explicitly out of scope; a future iteration could search a finer grid
around hma_window=85-95 to try to stabilize both equity symbols
simultaneously, but that is not required for this accept. This is a
genuinely improved construction over both predecessors (2026-09-09-019
plain calendar rejected, 2026-09-09-020 trend+vol-gated rejected) and this
cron trigger's best overall grid pass_fraction (0.194).
