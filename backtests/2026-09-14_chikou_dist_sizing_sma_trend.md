# Chikou Span (Ichimoku Lagging Line) Normalized-Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-163 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_chikou_dist_sizing_sma_trend.py`

## Hypothesis

Chikou Span (Ichimoku "lagging span"), per Investopedia/TrueData
(`web_search`'s DDG backend TLS-errored this query, `browser_exec` Google
search fallback used): the current period's closing price, conventionally
plotted `displacement` (default 26) periods back for visual sentiment
confirmation. Repo has 1 prior Chikou Span mention (2026-09-05-085), used
only as a 3rd AND-gate condition inside a full Ichimoku 3-line confluence
system, never isolated. This iteration isolates Chikou's own construction
as a standalone CONTINUOUS SIZING dial: normalized distance
(Close_t - Close_{t-displacement}) / Close_{t-displacement}, rolling
z-scored + tanh-squashed to [-1,1], sized within an SMA(trend_window)
uptrend gate, deadband + leverage_cap for crypto. First standalone Chikou
Span continuous-sizing variant.

Source: https://www.investopedia.com/terms/i/ichimokuchart.asp (Chikou
Span definition), cross-referenced with https://www.truedata.in/ichimoku-cloud-indicator
formula confirmation.

## Grid test summary (Step 6)

`param_grid={displacement: [9,26,52], sensitivity: [0.4,0.6,0.8]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 108, **passed:** 49, **pass_fraction:** 0.454.
- **by_asset_class:** equity 28/54 (0.519), crypto 21/54 (0.389).
- **by_vol_regime:** low 30/36 (0.833), mid 13/36 (0.361), high 6/36
  (0.167) — heavy high-vol degradation, consistent pattern this cron
  trigger.
- **best_cell:** QQQ, displacement=52/sensitivity=0.8, low-vol, Sharpe
  3.490.
- **worst_cell:** QQQ, displacement=52/sensitivity=0.8, high-vol, Sharpe
  -0.866.

## Single-config validator results (Step 7)

Best grid config (displacement=52, sensitivity=0.8) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.048 (pass) | 0.196 (pass) | 0.851 (pass) | 0.750 (pass) | 0.057 (pass) | **accepted** |
| SPY | 0.689 (**fail**, decisive) | 0.186 (pass) | 0.378 (**fail**) | 0.750 (pass) | 0.058 (pass) | **rejected** |
| BTC/USDT | 0.188 (**fail**, decisive) | 0.221 (pass) | -0.042 (**fail**) | 1.000 (pass) | 0.051 (pass) | **rejected** |
| ETH/USDT | 0.192 (**fail**, decisive) | 0.292 (**fail**) | -0.032 (**fail**) | 1.000 (pass) | 0.022 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** all 5 validators pass with comfortable margins at
leverage_cap=1.0, using an unusually long displacement=52 (52-day/~10-week
lookback, well beyond Ichimoku's classic 26-day default) as the winning
grid config.
**Rejected (SPY):** decisive Sharpe failure (0.689) and TC-survival
failure (0.378) — SPY's narrower historical range makes the long-lookback
distance dial too weak a signal relative to costs.
**Rejected (crypto):** BTC/USDT, ETH/USDT — decisive Sharpe and
TC-survival failures even at leverage_cap=0.4, ETH additionally fails MDD.
Consistent with this cron trigger's recurring finding that momentum/
distance-based sizing dials calibrated on multi-week daily-bar lookbacks
transfer poorly to crypto's different volatility/autocorrelation
structure. Narrower-but-honest QQQ-only acceptance recorded per
RESEARCH_LOOP.md Step 6 guidance.
