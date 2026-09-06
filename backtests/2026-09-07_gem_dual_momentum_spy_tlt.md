"""Backtest report: GEM Dual Momentum SPY/TLT (genuine bond safe-haven).

Hypothesis id: 2026-09-07-022
Strategy file: strategies/2026-09-07_gem_dual_momentum_spy_tlt.py
Outcome: **REJECTED**

## Background

2026-09-04-097 tested Antonacci's Dual Momentum GEM methodology using
QQQ-vs-SPY with CASH as the fallback safe haven (bond ETF data
unconfirmed at the time) and was rejected on max drawdown (28.6% vs 25%
threshold), with notes explicitly flagging "retest with a genuine
bond-ETF safe-haven if one becomes available via loaders.py" as a future
idea. This iteration confirms TLT (20+ Year Treasury) IS available via
`load_equity("TLT", ...)` and retests the ACTUAL original GEM pair: risk
asset (QQQ or SPY) vs TLT as the true bond safe-haven, with a strict
absolute-momentum gate (risk asset's own trailing return <=0 forces TLT
regardless of relative comparison, matching Antonacci's real rule, unlike
2026-09-04-097's softer "cash if either leg's absolute momentum is
non-positive" variant).

## Step 6 grid summary (lookback_days in [126,189,252], symbols QQQ/SPY,
crypto excluded -- no bond-ETF analog exists for BTC/ETH, same convention
as this repo's other cross-asset ratio strategies e.g. SPY/TLT SMA
2026-09-05-036, XLU/SPY 2026-09-05-067)

- total_cells: 18, passed_cells: 9, pass_fraction: **0.5**
- by_vol_regime: low 6/6 (1.0, clean pass), mid 3/6 (0.5), high 0/6 (0.0)
- best_cell: QQQ, lookback_days=189, low-vol regime, Sharpe 2.516

## Step 7 single-config validation (full 2019-2026 sample, all 3
lookbacks x QQQ/SPY)

| lookback | Symbol | Sharpe | MDD |
|---|---|---|---|
| 126 | QQQ | 0.453 FAIL | 0.443 FAIL |
| 126 | SPY | 0.317 FAIL | 0.419 FAIL |
| 189 | QQQ | **1.149 PASS** | **0.400 FAIL** |
| 189 | SPY | 0.889 FAIL | 0.333 FAIL |
| 252 | QQQ | 0.978 FAIL | 0.400 FAIL |
| 252 | SPY | 0.836 FAIL | 0.333 FAIL |

Best config (QQQ, lookback=189): Sharpe 1.149 (PASS), transaction-cost
survival at ~30 rebalance trades over 7.7yr net Sharpe 1.136 (PASS),
parameter sensitivity across the 3 lookbacks relative_std 0.345 (PASS) --
but **max drawdown 40.0%, decisively failing the 25% threshold**.

## Decision

**Rejected**, and MDD is the decisive, structural failure (not a
near-miss). Contrary to the working hypothesis in 2026-09-04-097's notes
("a real bond position would cushion drawdowns cash cannot"), swapping
cash for a genuine TLT bond position made the worst drawdown WORSE
(40.0% vs cash-variant's 28.6%), not better. The mechanism: 2022's
rate-hike cycle was an unusually severe episode where stocks AND
long-duration Treasuries fell together (TLT itself lost ~30%+ peak-to-
trough in 2022), breaking the historically-assumed negative stock-bond
correlation that GEM's safe-haven rotation depends on. Because the
absolute-momentum gate only re-evaluates monthly, the strategy could get
whipsawed INTO TLT near the top of its own decline once QQQ/SPY momentum
turned negative, then ride TLT down further before the next month-end
re-evaluation -- worse than sitting in flat cash during the same stretch.

This is a genuinely useful, non-obvious finding for a future loop: a
month-end-rebalanced GEM-style safe-haven rotation into long-duration
Treasuries is NOT a reliable drawdown cushion during a rate-hike / rising-
rate regime specifically, even though it may work better in other
historical periods GEM's original backtest (1970s-2013) covered. A future
loop could test a shorter-duration bond ETF (e.g. IEF/SHY, less rate-
sensitive) as the safe haven instead of TLT, or add a rate-regime filter
on top of the momentum comparison.

Source: https://www.quantifiedstrategies.com/spy-tlt-bond-rotation-strategy/
and https://www.quantifiedstrategies.com/dual-momentum-trading-strategy/
(same Antonacci GEM source already logged for 2026-09-04-097; TLT data
availability itself confirmed directly via `data/loaders.load_equity`,
no new external page fetch needed this iteration).
"""
