# Backtest Report: Yang-Zhang Calm-Regime Gate for SMA Trend-Following

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_yang_zhang_calm_regime_trend.py`
**Status:** REJECTED (full-sample Sharpe fail on both QQQ and SPY)

## Hypothesis

Per LuxAlgo's Yang-Zhang Estimator documentation (visited this iteration):
the Yang-Zhang estimator combines overnight (close-to-open) log-return
variance, open-to-close variance, and a Rogers-Satchell range term
(k=0.34/(1.34+(n+1)/(n-1)) weighting) into an OHLC-based realized
volatility measure that handles both opening gaps and price drift better
than close-to-close estimators. Source's own disclosed use: "the primary
estimate crossing above the slower comparison estimate signals volatility
expanding; crossing below, contracting... It is a sizing and regime
instrument, not a directional signal."

This strategy operationalizes that explicit regime-gate framing: only take
a plain SMA-crossover trend-following entry (close crosses above
SMA(trend_window)) while the Yang-Zhang volatility regime is CONTRACTING
(fast(20)-window estimate <= slow(60)-window estimate), exiting on the
mirror trend-cross, a regime flip to expanding, or a time-stop. Distinct
from this repo's already-tested Garman-Klass squeeze-breakout
(2026-09-08-023/044) and Parkinson expansion-cross/compression-reversion
pair (2026-09-09-027/028), which use their respective vol estimators as
the entry TRIGGER; here Yang-Zhang is used purely as an ongoing GATE on an
independent trend signal, matching the source's own stated intended use.

## Step 6 — Grid Test Summary

Grid: `fast_window` ∈ {15,20,25} × `slow_window` ∈ {50,60,80} ×
`trend_window` ∈ {100,150} × symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × 3
realized-vol terciles. 216 total cells.

- **Overall pass_fraction: 8.3%** (18/216 cells, min_sharpe=1.0, max_mdd=0.25)
- **By asset class:** equity 18/108 (16.7%); crypto 0/108 (0%, decisive reject)
- **By vol regime:** low 14/72 (19.4%); mid 0/72 (0%); high 4/72 (5.6%) —
  edge concentrates almost entirely in the low-vol tercile.
- **Best cell:** SPY, low-vol regime, fast=15/slow=50/trend=100, Sharpe
  **1.42**.
- **Worst cell:** SPY, mid-vol regime, fast=15/slow=80/trend=100, Sharpe
  **-0.64**.

## Step 7 — Single-Config Validators (full sample, 2019-01-01 to 2026-09-01)

Config: fast_window=15, slow_window=50, trend_window=100, max_hold_days=20
(the grid's best cell).

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **0.681 FAIL** | **0.435 FAIL** | ≥ 1.0 |
| Max drawdown | 0.144 PASS | 0.111 PASS | ≤ 0.25 |
| Transaction cost survival (10bps/trade) | 0.640 PASS | **0.388 FAIL** | ≥ 0.5 |
| Walk-forward (4-split manual date-slice fallback) | 0.75 PASS (3/4 splits positive) | 0.75 PASS (3/4 splits positive) | ≥ 0.75 |
| Parameter sensitivity (fast_window × slow_window sweep) | 0.107 PASS | 0.437 PASS | ≤ 0.5 |

Trade counts: QQQ 16 trades, SPY 13 trades — a low-frequency strategy
(long-only calm-regime SMA(100) crossovers over ~7.7 years).

## Step 8 — Decision: REJECT

Full-sample Sharpe fails decisively on both QQQ (0.681) and SPY (0.435),
consistent with the grid's own finding that the edge is concentrated
almost entirely in the low-vol tercile (19.4% pass rate) while mid-vol is
a complete washout (0/72). SPY additionally fails transaction-cost
survival despite its low trade count (13 trades) — the underlying gross
edge is simply too weak to survive even modest cost drag. Walk-forward and
parameter-sensitivity both pass (the low trade count keeps the strategy
mechanically stable across splits/param perturbations, but stability
around a sub-threshold Sharpe isn't useful). Crypto rejected decisively
(0/108 grid cells).

This is a genuine "the calm-regime gate doesn't add enough value over an
unconditional trend signal" rejection rather than an implementation flaw —
MDD is comfortably within budget and the strategy trades rarely enough
that costs aren't the primary driver of the QQQ failure. The Yang-Zhang
estimator's own documentation frames it purely as a regime/sizing tool
rather than a standalone edge source, and this test is consistent with
that framing: gating an already-marginal SMA(100) trend signal by a
volatility-contraction regime does not clear this repo's Sharpe bar.

The strategy file and this report are kept as a record of a rejected
attempt (not a live strategy).
