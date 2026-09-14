# STARC %B Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-144
**File:** `strategies/2026-09-14_starc_pctb_sizing_sma_trend.py`

## Hypothesis

STARC Bands (Stoller Average Range Channels, Manning Stoller): Upper = SMA(n)
+ K*ATR(n), Lower = SMA(n) - K*ATR(n) — an ATR-based (not std-dev-based)
volatility envelope. Source: LightningChart
(https://lightningchart.com/blog/en/starc-bands-stoller-average-range-channel-for-trading/),
visited via `browser_exec` (Google SERP + AI overview) after `web_search`
returned no usable text result for the query.

This repo has 2 prior STARC entries (2026-09-04-146, 2026-09-06-141), both
rejected binary lower-band-touch triggers. This iteration reframes STARC as
a Bollinger-%B-style CONTINUOUS SIZING dial:

```
starc_pctb = (close - lower) / (upper - lower)
dial = clip((starc_pctb - 0.5) * 2, -1, 1)
exposure = clip(base_exposure + sensitivity * dial, 0, leverage_cap)
exposure = exposure where trend_long (close > SMA(trend_window)) else 0
```
with a deadband to suppress churn, and leverage-cap-aware sizing for crypto
from the start (following this cron trigger's validated pattern).

## Grid test summary (Step 6)

`param_grid={starc_k: [1.0,1.5,2.0], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 75, **pass_fraction:** 0.521
- **by_asset_class:** equity 37/72 (0.514), crypto 38/72 (0.528)
- **by_vol_regime:** low 44/48 (0.917), mid 24/48 (0.5), high 7/48 (0.146)
  — as with most sizing-dial strategies this cron trigger, edge concentrates
  in low/mid realized-vol regimes and degrades sharply in high-vol regimes.
- **best_cell:** QQQ, starc_k=2.0/deadband=0.25/leverage_cap=1.0, low-vol,
  Sharpe 2.67
- **worst_cell:** QQQ, starc_k=1.5/deadband=0.25/leverage_cap=1.0, high-vol,
  Sharpe ~0.0

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | k=1.0, db=0.25, lc=0.4 | 1.335 (pass) | ~0.19 (pass) | pass | 1.0 (pass) | pass (rel_std low) | **accepted** |
| SPY | k=1.5, db=0.25, lc=0.4 | 1.098 (pass) | pass | **0.385 < 0.5 (FAIL)** | pass | pass | **rejected (near-miss on TC)** |
| BTC/USDT | k=2.0, db=0.15, lc=0.4 | 1.428 (pass) | 0.217 (pass) | pass (net Sharpe 1.139) | 1.0 (pass) | pass (rel_std 0.017) | **accepted** |
| ETH/USDT | k=1.5, db=0.15, lc=0.4 | 1.279 (pass) | 0.233 (pass) | pass (net Sharpe 1.088) | 1.0 (pass) | pass (rel_std 0.029) | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass at leverage_cap=0.4).
**Rejected:** SPY (near-miss, transaction-cost survival fails at 138 trades /
net Sharpe 0.385 vs 0.5 threshold; gross Sharpe/MDD/walk-forward/param-sensitivity
all pass — a genuine near-miss, candidate for a future deadband-widening
follow-up iteration).

Full raw grid: `grid_result_starc_pctb_sizing.json`. Full raw validators:
`validators_starc_pctb_sizing.json`.
