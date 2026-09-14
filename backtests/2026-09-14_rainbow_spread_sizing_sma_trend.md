# Rainbow Moving Average Fan-Out Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-158 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_rainbow_spread_sizing_sma_trend.py`

## Hypothesis

Rainbow Moving Average (per TradingView/WH SelfInvest/thinkorswim): a
cascade of N SMAs, each smoothing the prior one's output (`MA0=SMA(Close,
w)`, `MA_k=SMA(MA_{k-1}, w)`). Repo has 12 prior Rainbow entries (mostly
binary threshold/crossover triggers off the fan-out spread; one accepted,
per-symbol-tuned binary). This iteration uses the normalized fan-out
spread between fastest (MA0) and slowest (MA_last) band, `(MA0-MA_last)/
MA_last`, as a CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to
[-1,+1], sized within an SMA(trend_window) uptrend gate. Rationale: a
widely fanned-out rainbow indicates a mature, strongly-trending move
warranting larger exposure; a tightly bunched rainbow indicates
consolidation/low conviction. First Rainbow continuous-sizing variant.

Source: https://kr.tradingview.com/scripts/rainbow/ (via browser_exec —
web_search's DuckDuckGo backend failed with a TLS connection error for
this query), cross-referenced with WH SelfInvest/thinkorswim descriptions
shown inline in Google results.

## Grid test summary (Step 6)

`param_grid={band_window: [8,10,15], num_bands: [5,7]}`, symbols QQQ/SPY
(equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 27, **pass_fraction:** 0.375.
- **by_asset_class:** equity 18/36 (0.5), crypto 9/36 (0.25).
- **by_vol_regime:** low 19/24 (0.792), mid 6/24 (0.25), high 2/24 (0.083).
- **best_cell:** QQQ, band_window=15/num_bands=5, low-vol, Sharpe 3.23 —
  highest single-cell Sharpe of any strategy this cron trigger.
- **worst_cell:** QQQ, band_window=15/num_bands=7, high-vol, Sharpe -0.83.

## Single-config validator results (Step 7)

Best grid config (band_window=15, num_bands=5, sensitivity=0.6) tested per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | 130 | 1.094 (pass) | 0.200 (pass) | 0.785 (pass) | 0.75 (pass) | 0.025 (pass) | **accepted** |
| SPY | 148 | 0.795 (**fail**) | 0.173 (pass) | 0.357 (**fail**) | 0.75 (pass) | 0.074 (pass) | **rejected** |
| BTC/USDT | 115 | 1.243 (pass) | 0.223 (pass) | 1.072 (pass) | 1.0 (pass) | 0.074 (pass) | **accepted** |
| ETH/USDT | 133 | 0.888 (**fail**) | 0.229 (pass) | 0.749 (pass) | 1.0 (pass) | 0.127 (pass) | **rejected** |

## Decision

**Accepted (QQQ, BTC/USDT):** all 5 validators pass.
**Rejected (SPY, ETH/USDT):** both fail on gross Sharpe alone (SPY
decisively 0.795, ETH near-miss 0.888); other 4 validators pass for both.

Scope note: unusual asymmetry this cron trigger — the two crypto symbols
split (BTC accept, ETH reject) rather than moving together as most other
overlays this run did; treat this as symbol-specific rather than a clean
asset-class generalization. QQQ+BTC is a genuinely narrower but honest
accept.

Full raw grid: `/tmp/rainbow_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_rainbow_spread_sizing.json`.
