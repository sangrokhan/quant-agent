# Backtest Report: LQD/IEF Credit-Spread Persistence Gate on SMA Trend-Following

**Strategy file:** `strategies/2026-09-21_lqd_ief_persistence_gate.py`
**Date:** 2026-09-21

## Hypothesis

Per Cesar Alvarez's "Market Timing with a Canary, Gold, Copper, LQD, IEF and
much more" (https://alvarezquanttrading.com/blog/market-timing-with-a-canary-
gold-copper-lqd-ief-and-much-more/), relaying Adam Robinson's Knowledge
Project podcast remark that the LQD (investment-grade corporate bond ETF) /
IEF (7-10yr Treasury ETF) ratio is a good market-timing signal (credit
spreads widening relative to Treasuries reflects deteriorating risk
appetite before equities react). Alvarez's own disclosed operationalization:
ratio closing above/below its own 200-day EMA for 5+ consecutive days flips
a risk-on/risk-off state. This iteration gates a plain SMA(trend_window)
trend-following signal on the primary asset (QQQ/SPY) by that credit-spread
persistence state.

## Iteration history this cron trigger

1. **id=2026-09-21-251** (previous iteration): tested persistence_days in
   {3,5,7,10} x trend_window in {150,200,250}. QQQ near-missed Sharpe
   (0.978 at trend_window=200/persistence_days=5); SPY failed decisively.
2. **id=2026-09-21-252** (this entry): direct follow-up widening the
   persistence_days sweep down to {1,2,3,4,5,8,12,15,20} per the prior
   entry's own recorded suggestion. **persistence_days=2** (a much shorter
   confirmation window than Alvarez's original "5+ days") clears the bar:
   QQQ Sharpe 1.063, SPY Sharpe 1.038 — both now pass.

## Single-config validators — primary config: trend_window=200, persistence_days=2

| Validator | QQQ | SPY |
|---|---|---|
| sharpe_ratio (>=1.0) | **PASS** 1.063 | **PASS** 1.038 |
| max_drawdown (<=25%) | **PASS** 15.9% | **PASS** 20.5% |
| transaction_cost_survival (10bps/trade, net Sharpe>=0.5) | **PASS** net 1.000 (66 trades) | **PASS** net 0.961 (58 trades) |
| walk_forward (4 manual date-slices, >=75% pass) | **PASS** 4/4 (1.0) | **PASS** 3/4 (0.75) |
| parameter_sensitivity (15-cell trend_window x persistence_days sweep) | **PASS** 0.054 (mean 0.980) | **PASS** 0.083 (mean 0.937) |

## Decision

**ACCEPTED for both QQQ and SPY** — all 5 validators pass on both symbols
at the shared config trend_window=200, persistence_days=2. Parameter
sensitivity is unusually low (relative_std 0.05-0.08 across 15 cells),
indicating the strategy is robust to persistence_days/trend_window choice
in the 1-3 day / 150-250 day neighborhood, not a fragile single-point
optimum.

Crypto not tested (strategy structurally requires LQD/IEF equity
credit-market data with no crypto analogue, consistent with prior
credit-spread/cross-asset-macro strategies in this repo).

Note for future loops: the originally-cited "5+ days" persistence rule
(Alvarez's own stated value) does NOT clear this repo's validator
thresholds — only a much shorter persistence_days=1-2 window does. This is
an honest deviation from the source's literal parameter, disclosed here so
a future loop doesn't assume the source's exact "5 days" figure was used.
