# Growth-vs-Value (IWF/IWD) factor-rotation trend-confirmation gate (ACCEPTED, QQQ only)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_iwf_iwd_growth_value_rotation_gate.py`
**Source:** https://getnick.ai/strategies/growth-vs-value-factor-rotation

## Hypothesis
A disclosed mechanical construction for timing growth-vs-value factor
rotation: build the IWF/IWD ratio (growth ETF over value ETF), compare
it to its own 20-day and 50-day moving averages, and use that alignment
as a regime classifier (short MA above long MA = growth regime intact).
Adapted as a trend-confirmation gate: stay long the primary asset (QQQ,
a growth-tilted broad-index proxy) only while (a) its own price is in
an uptrend (close > SMA(trend_window)) AND (b) the IWF/IWD ratio's fast
SMA is above its slow SMA (growth regime confirmed). Mirrors the
regime-confirmation-gate pattern already validated for SPHB/SPLV
(2026-09-20-049, accepted) but with a distinct factor pair (growth/value
style tilt) and a dual-SMA-alignment condition instead of a rolling-high
proximity condition. For crypto (no growth/value factor-ETF analogue),
the gate degrades to a plain SMA trend-follow.

## Grid test summary

trend_window in {50,100,150} x ratio_fast in {10,20,30} x ratio_slow in
{50,80}, symbols IWF/QQQ, vol_regime_splits=3, 2019-2026 (108 cells)

- pass_fraction: 0.648 (70/108) -- the strongest grid pass_fraction of
  any strategy this cron trigger
- by_vol_regime: low 36/36 (perfect), mid 34/36, high 0/36
- best_cell: QQQ, trend_window=50, ratio_fast=10, ratio_slow=50,
  low-vol, Sharpe 3.01
- worst_cell: IWF, trend_window=50, ratio_fast=30, ratio_slow=80,
  high-vol, Sharpe -1.28

## Single-config validators (QQQ, trend_window=150, ratio_fast=30, ratio_slow=50, full 2019-2026 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.138 | >= 1.0 | PASS |
| Max drawdown | 0.244 | <= 0.25 | PASS (narrow margin) |
| Transaction cost survival (10bps, 19 trades) | 1.116 | >= 0.5 | PASS |
| Walk-forward (manual 4-split, repo convention) | 0.75 (3/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (ratio_fast in {20,25,30,35,40}) | relative_std 0.042 | <= 0.5 | PASS |

All 5 validators pass for QQQ. Note the max-drawdown margin (24.4% vs
25% cap) is thin -- flagged for future monitoring as data accrues, same
caveat pattern used for other narrow-margin accepts in this repo.

## Cross-symbol scope check (same config)

| Symbol | Sharpe | MDD | TC-survival |
|---|---|---|---|
| QQQ | 1.138 PASS | 0.244 PASS (thin) | 1.116 PASS |
| IWF (the growth ETF itself) | 0.956 FAIL (near-miss) | 0.198 PASS | 0.921 PASS |
| BTC/USDT (degraded gate) | 1.019 PASS | 0.444 FAIL | 1.008 PASS |
| ETH/USDT (degraded gate) | 0.839 FAIL | 0.679 FAIL | 0.831 PASS |

## Decision: ACCEPTED (QQQ only, narrow-margin MDD)

Strategy file and this report kept as a live accepted strategy, strictly
scoped to QQQ at trend_window=150/ratio_fast=30/ratio_slow=50. IWF
(the underlying growth ETF the ratio itself is built from) narrowly
misses Sharpe at this exact config -- a future loop could retune
IWF-specific parameters. Crypto legs decisively fail for the same
architectural reason as the SPHB/SPLV strategy (no factor-ETF analogue,
degraded gate inherits crypto's larger drawdowns) -- do not apply to
crypto.

## Notes for future loops
- This has the highest grid pass_fraction (64.8%) of any strategy
  tested this cron trigger, and is a perfect 36/36 in the low-vol
  tercile -- strong signal that the growth/value rotation confirmation
  mechanism is genuinely robust in calm markets, degrading only in
  high-vol regimes (0/36), consistent with most trend-following gates
  in this repo.
- MDD passes QQQ by only 0.6 percentage points (24.4% vs 25.0% cap) --
  this is the tightest margin of any validator in this entry. A future
  loop revisiting this strategy should not assume it's robustly above
  the drawdown threshold and should reconsider if MDD threatens to
  breach as new data accrues (same caveat pattern as 2026-09-20-046's
  10Y Treasury COT gate, which had an identical near-25%-cap MDD).
- Distinct from all prior "ratio SMA crossover" style strategies (e.g.
  2026-09-05-034 RSP/SPY equal-weight rotation) via the growth/value
  factor pair specifically -- first use of IWF/IWD in this repo.
