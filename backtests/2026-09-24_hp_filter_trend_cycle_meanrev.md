# HP Filter Trend/Cycle Mean-Reversion — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_hp_filter_trend_cycle_meanrev.py`
**Status: REJECTED** (full-sample Sharpe fails threshold)

## Hypothesis

Source: https://sourcetable.com/ai-trading-strategies/fx-moving-averages-hp-filter
(via Google SERP fallback, web_search backend erroring this iteration).

The Hodrick-Prescott (HP) filter decomposes price into a smooth trend
component (tau) and a cyclical residual (c = price - tau), where tau is
derived by minimizing `Σ(y-tau)^2 + lambda*Σ[(tau_{t+1}-tau_t)-(tau_t-tau_{t-1})]^2`
rather than a simple moving average. Source's own stated rule: "Define
oversold as cyclical component below -1.5 standard deviations ...
historically these setups precede mean-reversion moves." Implemented here
as: enter long when the z-scored cycle (c / rolling_std(c)) <= -entry_z,
exit when z >= exit_z or after max_hold_days. Causal rolling re-fit (each
bar's trend uses only its own trailing hp_window window, keeping the
endpoint value) to respect the source's own "end-point problem" caveat and
avoid lookahead. First HP-filter strategy in this repo (zero prior
"Hodrick-Prescott"/"HP Filter" hits in `knowledge_base/strategies_index.jsonl`).

## Step 6 — Grid test summary

Grid: `hp_window` in {40, 60} × `entry_z` in {1.5, 2.0}, symbols
equity=[QQQ], crypto=[BTC/USDT], vol_regime_splits=3 (light workload:
1 symbol per asset class). 24 total cells.

- `pass_fraction`: 0.167 (4/24)
- `by_asset_class`: equity 4/12 passed, crypto 0/12 passed
- `by_vol_regime`: low 4/8 passed, mid 0/8, high 0/8
- `best_cell`: hp_window=40, entry_z=1.5, QQQ, low-vol regime, Sharpe=2.339
- `worst_cell`: hp_window=60, entry_z=2.0, BTC/USDT, low-vol regime, Sharpe=-0.020

Finding: this edge is narrow — only shows up in equity/low-vol-regime
cells; crypto decisively fails across every cell and parameter combo
tested, and mid/high vol regimes fail on equity too.

## Step 7 — Single-config validators (QQQ, hp_window=40, entry_z=1.5,
exit_z=0.0, max_hold_days=15, lambda_=1600, full sample 2019-01-01 to
2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.731 | >= 1.0 |
| Max drawdown | PASS | 0.178 | <= 0.25 |
| TC survival (10bps/trade, 134 trades) | PASS | 0.552 net Sharpe | >= 0.5 |
| Walk-forward (4 splits, manual since vbt.utils.splitting API unavailable) | PASS | 0.75 pass fraction | >= 0.75 |
| Parameter sensitivity (4-cell QQQ grid) | PASS | 0.212 relative std | <= 0.5 |

## Decision: REJECT

Full-sample Sharpe (0.731) misses the 1.0 threshold despite the grid's
best single-vol-regime cell showing Sharpe 2.34 — the strategy's edge is
concentrated in low-vol regimes and doesn't survive averaged across the
full sample including mid/high-vol periods. 4/5 validators pass but Sharpe
is the primary gate. Leaving strategy file in `strategies/` as a rejected
record (not live).

## Notes for future iterations

A regime-gated variant (only trade when in a low-vol regime, matching the
already-established pattern used by e.g. `2026-09-03_bb_meanrev_qqq_volregime.py`)
could plausibly rescue this — the raw grid data already shows the low-vol
cells alone clear Sharpe >1 (best_cell 2.339). Not attempted this iteration
(single-iteration scope); flagged as a concrete retune candidate for a
future loop.
