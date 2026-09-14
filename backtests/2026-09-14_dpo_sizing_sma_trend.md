# Detrended Price Oscillator (DPO) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-154 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_dpo_sizing_sma_trend.py`

## Hypothesis

Detrended Price Oscillator (DPO), per ChartSchool/Investopedia/TradingView:
`DPO_t = Close_{t-(n/2+1)} - SMA_n(Close)_t` — the close price from n/2+1
bars ago minus the n-period SMA. Unlike OBV/PVT/ADL (cumulative running
totals needing rate-of-change reframing this cron trigger), DPO is already
a bounded, zero-centered oscillator by construction (it strips trend via
the displaced SMA), so it can be used directly (no diff/roc needed) as a
continuous sizing dial. Repo has 3 prior DPO entries (2026-09-04-056 binary
crossover; 2026-09-06-139 trough/peak-turn timing; 2026-09-08-049
cycle-timing + quantile-regime-gate), none using raw DPO as a continuous
z-scored sizing multiplier. This iteration: rolling z-score of raw DPO,
tanh-squashed to [-1,+1], sized within an SMA(trend_window) uptrend gate,
with a deadband and leverage_cap for crypto.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/detrended-price-oscillator-dpo
(via web_search, confirmed cross-reference with Investopedia/TradingView/Wikipedia formulas in search results).

## Grid test summary (Step 6)

`param_grid={dpo_window: [15,20,30], sensitivity: [0.5,0.7]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 38, **pass_fraction:** 0.528.
- **by_asset_class:** equity 21/36 (0.583), crypto 17/36 (0.472).
- **by_vol_regime:** low 18/24 (0.75), mid 15/24 (0.625), high 5/24 (0.208)
  — typical pattern this cron trigger: sizing overlays degrade sharply in
  high-vol terciles.
- **best_cell:** SPY, dpo_window=20/sensitivity=0.5, low-vol, Sharpe 2.82.
- **worst_cell:** QQQ, dpo_window=20/sensitivity=0.7, high-vol, Sharpe -0.54.

## Single-config validator results (Step 7)

Best grid config (dpo_window=20, sensitivity=0.5) tested per symbol with
leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.719 (**fail**, thr 1.0) | 0.166 (pass) | -0.150 (**fail**, thr 0.5) | 0.75 (pass) | 0.157 (pass) | **rejected** |
| SPY | 0.941 (**fail**, thr 1.0, near-miss) | 0.108 (pass) | -0.133 (**fail**, thr 0.5) | 0.75 (pass) | 0.086 (pass) | **rejected** |
| BTC/USDT | 1.439 (pass) | 0.180 (pass) | 0.730 (pass) | 1.0 (pass) | 0.095 (pass) | **accepted** |
| ETH/USDT | 1.103 (pass) | 0.202 (pass) | 0.664 (pass) | 1.0 (pass) | 0.077 (pass) | **accepted** |

## Decision

**Accepted (crypto only):** BTC/USDT, ETH/USDT — all 5 validators pass.
**Rejected (equity):** QQQ, SPY — both fail Sharpe (QQQ decisively, SPY a
near-miss) AND transaction-cost survival (net Sharpe goes negative after
costs at 506/505 trades over the sample — this strategy trades too
frequently on equity daily bars relative to its raw edge there).

Scope note for future loops: this DPO continuous-sizing dial only holds up
on crypto (BTC/ETH) at leverage_cap=0.4; do not assume it generalizes to
equity daily bars without a lower-turnover variant (e.g. wider deadband or
longer zscore_window to reduce whipsaw trade count).

Full raw grid: `/tmp/dpo_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_dpo_sizing.json`.
