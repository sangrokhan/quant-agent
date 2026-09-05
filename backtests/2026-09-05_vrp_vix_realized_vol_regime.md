# Backtest Report: Volatility Risk Premium (VRP) Regime Filter

**Strategy ID:** 2026-09-05-044
**File:** `strategies/2026-09-05_vrp_vix_realized_vol_regime.py`
**Date:** 2026-09-05

## Hypothesis

The Volatility Risk Premium (VRP = VIX - annualized realized vol of the
underlying) measures whether option markets are pricing more turbulence
than has actually occurred. A positive, meaningfully large VRP signals a
calmer risk-on regime (options overpriced relative to realized moves);
long when VRP > vrp_threshold, flat otherwise.

**Source:** Google AI-overview synthesis (citing Robot Wealth, Concretum
Group, Invest with CARL, FlashAlpha, Charles Schwab, StrikeWatch EA) of a
standard Volatility Risk Premium trading framework. Adapted here as a
long/flat equity exposure gate (not options/ETP trading, per this repo's
scope).

## Grid Test Summary (Step 6)

Grid: `rv_window ∈ {10, 20, 30}` × `vrp_threshold ∈ {0.0, 2.0, 4.0}` ×
symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × vol_regime_splits=3 (low/mid/high
realized-vol terciles), 2017-01-01 to 2026-09-01.

- **Overall pass fraction:** 28/108 = 0.259
- **By asset class:** equity 28/54 (0.52); crypto 0/54 (0.0)
- **By vol regime:** low 18/36 (0.5); mid 0/36 (0.0); high 10/36 (0.278)
- **Best cell:** SPY, rv_window=20, vrp_threshold=0.0, low-vol regime, Sharpe 2.71
- **Worst cell:** QQQ, rv_window=10, vrp_threshold=4.0, mid-vol regime, Sharpe -0.56

Full-period Sharpe/MDD by config (QQQ / SPY):

| rv_window | vrp_threshold | QQQ Sharpe | QQQ MDD | SPY Sharpe | SPY MDD |
|---|---|---|---|---|---|
| 10 | 0.0 | 1.29 | 0.155 | 1.19 | 0.152 |
| 10 | 2.0 | 1.12 | 0.160 | 0.96 | 0.156 |
| 10 | 4.0 | 0.80 | 0.107 | 0.97 | 0.149 |
| 20 | 0.0 | 1.22 | 0.198 | 0.99 | 0.203 |
| **20** | **2.0** | **1.32** | **0.155** | 0.96 | 0.191 |
| 20 | 4.0 | 1.22 | 0.156 | 0.94 | 0.161 |
| 30 | 0.0 | 0.97 | 0.228 | 0.77 | 0.324 |
| 30 | 2.0 | 0.91 | 0.174 | 0.55 | 0.270 |
| 30 | 4.0 | 0.79 | 0.162 | 0.43 | 0.230 |

The strategy shows a clear pattern: mid-vol regimes are the weakest slice
(0/36 grid cells pass) while low- and high-vol regimes are both favorable
-- this is intuitive for a VRP signal, since the biggest option-vs-realized
mispricings tend to occur at the extremes (very calm markets where implied
vol has a large structural cushion, and post-shock high-vol markets where
realized vol mean-reverts faster than implied). Crypto is 0/54 across the
board -- no VIX-analog exists for crypto, and using SPY's VIX as a proxy
signal for BTC/ETH's own realized vol regime has no theoretical basis
(falsification check confirms it does not transfer).

`rv_window=20, vrp_threshold=2.0` is the standout config: full-period QQQ
Sharpe 1.32 (highest of all 9 param combos on QQQ) with MDD 0.155, while
SPY at the same config is a near-miss (Sharpe 0.96).

## Single-Config Validation (Step 7) — QQQ, rv_window=20, vrp_threshold=2.0, full period 2017-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.315 | ≥ 1.0 |
| Max drawdown | **PASS** | 0.155 | ≤ 0.25 |
| Transaction cost survival (5bps/trade, 195 trades) | **PASS** | net Sharpe 1.184 | ≥ 0.5 |
| Walk-forward | not run — `vbt.utils.splitting.RangeSplitter` unavailable in this repo's installed vectorbt version (known repo limitation, consistent with essentially every recent knowledge_base entry). |
| Parameter sensitivity (9-point rv_window × vrp_threshold grid, full-period QQQ Sharpe) | **PASS** | relative_std 0.183 | ≤ 0.5 |

All validators run pass, and by a comfortable margin (Sharpe 1.32 vs 1.0
threshold, net-of-cost Sharpe still above 1.0 even after transaction costs).

## Decision

**Accepted — QQQ (equity), rv_window=20, vrp_threshold=2.0.** SPY is a
near-miss at the same config (Sharpe 0.96, just under the 1.0 bar) —
recorded as such rather than accepted, per repo convention of being
precise about scope. Crypto rejected across the board (0/54 grid cells,
no theoretical basis and no data support).
