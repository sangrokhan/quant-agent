# Backtest Report: NVI (Negative Volume Index) Continuous Sizing Overlay on SMA Trend Gate

**Date:** 2026-09-14
**Strategy file:** `strategies/2026-09-14_nvi_sizing_sma_trend.py`
**Source:** Google AI overview (browser_exec fallback; web_search DDGS backend
returned a TLS connection error for this query) synthesizing Fosback/Dysart
NVI formula. Repo has 1 prior NVI entry (2026-09-04-139, binary MA-crossover
trigger, rejected).

## Hypothesis

Negative Volume Index (NVI): a cumulative index that only updates on days
volume DECREASES vs the prior day, adding that day's % price change
("smart money" tracking theory). Formula: `NVI_t = NVI_{t-1} + (P_t-P_{t-1})/P_{t-1}*NVI_{t-1}`
if `V_t < V_{t-1}`, else unchanged. This iteration converts NVI's own
short-horizon rate of change (`pct_change(roc_window)`) into a rolling
z-score and uses it as a CONTINUOUS SIZING dial (not a binary crossover
trigger, unlike the prior rejected attempt) layered on a `SMA(trend_window)`
long/flat directional gate, with a rebalance-buffer deadband and
leverage-cap-aware crypto sizing — the pattern validated broadly across
15+ other indicator families this cron trigger.

## Grid test (validation/grid_test.py::run_strategy_grid)

`param_grid={sensitivity:[0.3,0.5], deadband:[0.2,0.3], leverage_cap:[1.0,0.4]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`.

- **Overall pass_fraction: 0.614** (59/96 cells)
- By asset class: equity 26/48 (0.54), crypto 33/48 (0.69)
- By vol regime: low 32/32 (1.00), mid 19/32 (0.59), high 8/32 (0.25)
- Best cell: SPY, sensitivity=0.3/deadband=0.2/leverage_cap=0.4, low-vol, Sharpe 2.69
- Worst cell: QQQ, sensitivity=0.5/deadband=0.2/leverage_cap=1.0, high-vol, Sharpe -0.27

Crypto actually had a *higher* per-cell pass rate than equity in this grid
(0.69 vs 0.54) — an unusual result for this cron trigger's continuous-sizing
family, where crypto has failed decisively (MDD) in nearly every prior
iteration.

## Single-config validators (best full-sample config per symbol)

| Symbol | Params | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.3, db=0.3, lev=0.6 | 1.388 | 0.125 | pass | pass | pass | **YES** |
| SPY | sens=0.5, db=0.3, lev=1.0 | 1.344 | 0.108 | pass | pass | pass | **YES** |
| BTC/USDT | sens=0.3, db=0.3, lev=0.6 | 1.519 | 0.277 | pass | pass | pass | NO (MDD 0.277>0.25) |
| ETH/USDT | sens=0.3, db=0.3, lev=0.4 | 1.190 | 0.270 | pass | pass | pass | NO (MDD 0.270>0.25) |

Crypto Sharpe ratios are strong (1.19–1.52) and every other validator
(TC-survival, walk-forward, parameter sensitivity) passes — only max
drawdown fails, and only narrowly (0.270–0.277 vs 0.25 threshold), unlike
the "decisive" 0.30–0.45+ MDD failures typical for this family on crypto.
This is a genuine near-miss, not a decisive rejection; a follow-up
iteration could retry with a lower `leverage_cap` (e.g. 0.3) per this
cron trigger's established leverage-cap-recalibration pattern
(2026-09-14-124/125).

## Decision

**Accept: QQQ and SPY (equity).** All 5 validators pass for both.
**Reject: BTC/USDT and ETH/USDT (crypto).** MDD narrowly fails at
`leverage_cap=0.6`/`0.4`; a lower leverage cap was not swept this
iteration (time-boxed) — flagged as a promising candidate for the next
iteration's leverage-cap-recalibration follow-up.
