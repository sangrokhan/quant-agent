# Coppock Curve Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-171 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_coppock_sizing_sma_trend.py`

## Hypothesis

Coppock Curve (Edwin "Sedge" Coppock, 1962/1965): Curve = WMA(wma_window) of
[ROC(close, roc1_period) + ROC(close, roc2_period)], WMA applying linearly
increasing weights favoring recent values. This repo has 14+ prior Coppock
Curve entries, ALL using it as a BINARY zero-line-crossover or trough/peak-
turn ENTRY trigger (one accepted QQQ-only via zero-cross, 2026-09-04-036).
None used Coppock's own continuous magnitude as a SIZING dial. This
iteration reframes Coppock as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], sized within an SMA(trend_window) uptrend gate,
deadband + leverage_cap for crypto. First Coppock Curve continuous-sizing
variant in this repo.

Source: Google AI-overview synthesis (browser_exec fallback -- web_search's
DuckDuckGo backend returned "No results found" for this iteration's query)
of LightningChart's Coppock Curve guide and StockCharts ChartSchool's
SharpCharts calculation definition (Coppock Curve = 10-period WMA of
14-period RoC + 11-period RoC).

## Grid test summary (Step 6)

`param_grid={wma_window: [10,20], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 33, **pass_fraction:** 0.458.
- **by_asset_class:** equity 19/36 (0.528), crypto 14/36 (0.389).
- **by_vol_regime:** low 21/24 (0.875), mid 8/24 (0.333), high 4/24 (0.167).
- **best_cell:** QQQ, wma_window=10/sensitivity=0.6, low-vol, Sharpe 3.035.
- **worst_cell:** SPY, wma_window=20/sensitivity=0.4, mid-vol, Sharpe -0.294.

## Single-config validator results (Step 7)

Best grid config (wma_window=10, sensitivity=0.6) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.180 (pass) | 0.119 (pass) | 0.640 (pass) | 1.000 (pass) | 0.067 (pass) | **accepted** |
| SPY | 0.938 (**fail**, near-miss) | 0.079 (pass) | 0.346 (**fail**) | 0.750 (pass) | 0.083 (pass) | **rejected** |
| BTC/USDT | 0.177 (**fail**, decisive) | 0.299 (**fail**) | -0.058 (**fail**) | 0.750 (pass) | 0.220 (pass) | **rejected** |
| ETH/USDT | 0.230 (**fail**, decisive) | 0.244 (pass) | -0.049 (**fail**) | 1.000 (pass) | 0.229 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** clears all 5 validators at leverage_cap=1.0 --
Coppock's dual-ROC WMA-smoothed composite momentum, reframed as a
continuous sizing dial rather than a binary zero-line/trough-turn trigger,
rescues an indicator family that has otherwise saturated 14+ prior binary-
trigger entries in this repo with only 1 prior acceptance.
**Rejected (SPY):** near-miss Sharpe (0.938 vs 1.0 threshold) and TC-
survival fails outright (0.346 vs 0.5), the same recurring pattern seen
across nearly every equity sizing-dial variant this cron trigger where QQQ
clears comfortably but SPY's lower realized vol under the same config
compresses net Sharpe below threshold after cost drag.
**Rejected (crypto):** BTC/USDT, ETH/USDT -- decisive Sharpe/TC-survival
failures even at leverage_cap=0.4, consistent with this cron trigger's
recurring finding that daily-bar-calibrated momentum/ROC-based sizing dials
transfer poorly to crypto's higher-frequency regime.
