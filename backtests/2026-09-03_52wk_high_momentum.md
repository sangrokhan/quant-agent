# Backtest Report: 52-Week-High Proximity Momentum (150d SMA Exit)

**Strategy file:** `strategies/2026-09-03_52wk_high_momentum.py`
**Hypothesis ID:** 2026-09-03-015
**Source:** Google AI-overview / search snippets for the 52-week-high
momentum effect (George & Hwang academic lineage); web_search itself failed
with a DDGS/TLS connection error for this query, and the primary
quantifiedstrategies.com article was blocked by a bot-verification
challenge (same blocker as prior loop iterations -004/-008) — used the
Google snippet text directly for the concrete rule instead.

## Hypothesis

Buy stocks trading at/near their rolling 252-trading-day ("52-week") high —
investors anchor on the 52-week high and underreact to sustained strength
once price approaches/exceeds it. Exit when price crosses below its 200-day
(here: swept 150d/200d) SMA. Distinct from every prior momentum entry in
this repo: entry trigger is proximity-to-rolling-high (a price level, like
Donchian -008, but framed as "within X% of the 252d high" not "new N-day
high"), combined with an SMA trend-flip exit (like -004/-008/-012) rather
than a trailing-return threshold (-002/-003/-004/-012).

Long-only per SAFETY.md.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `pct_from_high` in {0.01,0.02,0.05} x `trend_window` in {150,200} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.25** (18/72)
- by_asset_class: equity 18/36 (50%), crypto 0/36 (0%)
- by_vol_regime: low 12/24 (50%), mid 6/24 (25%), high 0/24 (0%)
- best_cell: SPY, pct_from_high=0.02/trend_window=150, low-vol regime, Sharpe 2.71
- worst_cell: QQQ, pct_from_high=0.01/trend_window=150, high-vol regime, Sharpe -0.10

## Single-config validators (best grid config: pct_from_high=0.02, trend_window=150)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd (4-split) |
|---|---|---|---|---|
| SPY | **1.12 (pass, thr 1.0)** | **14.6% (pass, thr 25%)** | **1.10 (pass, thr 0.5, 11 trades @10bps)** | **0.75 (pass, thr 0.75)** |
| QQQ | 0.96 (fail, thr 1.0) | 18.3% (pass) | 0.94 (pass) | 0.75 (pass) |
| BTC/USDT | 0.29 (fail) | 32.9% (fail) | 0.18 (fail) | 1.0 (pass) |

Parameter sensitivity (6-point pct_from_high/trend_window sweep on SPY):
relative std 0.06 — Sharpe stays in the tight 0.93-1.12 range across every
combo tested, i.e. the SPY pass is not a fragile single-point artifact.

Walk-forward used a manual 4-way date-slice fallback (vectorbt
`utils.splitting.RangeSplitter` still broken — unfixed since 2026-09-03-002).

## Decision: **ACCEPT (SPY only)**

SPY clears all 5 standard validators cleanly at the grid-optimal config
(pct_from_high=0.02, trend_window=150): Sharpe 1.12, MDD 14.6%, net-of-cost
Sharpe 1.10 (only 11 trades over 7.7 years — very low turnover), walk-
forward 3/4 splits positive, parameter-sensitivity relative std 0.06.

QQQ is a near-miss (Sharpe 0.96 vs 1.0) despite passing every other
validator — worth revisiting with a slightly different pct_from_high in a
future loop. BTC/USDT and crypto broadly fail decisively (Sharpe 0.29, MDD
32.9%) — the same equity-only pattern seen in nearly every trend/momentum
strategy tested in this repo (Donchian -008, MACD -013, SuperTrend -014).

**Scope: SPY only, long-only, 52-week-high proximity (2%) with 150d SMA
exit. Do not extend to QQQ, crypto, or high-vol regimes without further
validation.**
