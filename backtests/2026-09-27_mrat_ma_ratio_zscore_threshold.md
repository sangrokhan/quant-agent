# Backtest Report: MRAT (Moving Average Ratio) Z-Score Threshold (2026-09-27)

## Hypothesis

Per https://aligrithm.com/moving-average-distance-the-technical-indicator-that-passed-the-cross-section/
(Ali H. Askar, Aligrithm, Sep 23 2026, summarizing Avramov/Kaplanski/
Subrahmanyam's academic "Moving Average Distance" cross-sectional factor
paper, read via `browser_exec` fallback -- `web_extract`'s ddgs backend
cannot fetch page content): MRAT = MA(21)/MA(200); the paper's cross-
sectional long leg (top decile, MRAT > 1+sigma) earns 9.05% annual alpha,
while a plain golden-cross/death-cross BINARY event dummy is dead
(t-stat 1.17). This repo's single-symbol architecture adapts the mechanism
to a time-series threshold: rolling-z-score MRAT against its own trailing
252-day distribution, long when z > entry_threshold, exit when z falls
below a lower exit_threshold or a max_hold_days time-stop.

Distinct from this repo's existing binary MA-crossover strategies (which
the source itself says should be flat) and from cross-ASSET MA-ratio
regime filters like 2026-09-05-068 (Growth/Value ETF ratio).

## Grid test summary (Step 6)

param_grid: entry_threshold=[0.75,1.0,1.5], exit_threshold=[0.0,0.3],
max_hold_days=[40,60]; symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT];
vol_regime_splits=3 (2018-01-01 to 2026-09-01).

- total_cells: 144, passed_cells: 40, **pass_fraction: 0.278**
- by_asset_class: equity 22/72 passed, crypto 18/72 passed (both asset
  classes show real signal, unlike many prior single-asset-class hits)
- by_vol_regime: low 24/48, mid 16/48, **high 0/48** (fails universally in
  high-vol regime, as expected for a trend-persistence-style signal)
- best_cell: QQQ, mid-vol, entry_threshold=1.0/exit_threshold=0.3/
  max_hold_days=60, Sharpe=2.26
- worst_cell: QQQ, high-vol, entry_threshold=1.5/exit_threshold=0.0/
  max_hold_days=60, Sharpe=-1.16

## Single-config validators (Step 7) -- best_cell config, full sample, all 4 symbols

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.541 FAIL | 0.252 FAIL | 0.531 PASS | 0.50 FAIL | 0.796 FAIL | 9 |
| SPY | 0.385 FAIL | 0.172 PASS | 0.365 FAIL | 0.75 PASS | 1.029 FAIL | 11 |
| BTC/USDT | 1.012 PASS | 0.361 FAIL | 1.006 PASS | 1.00 PASS | 0.083 PASS | 17 |
| ETH/USDT | 0.474 FAIL | 0.740 FAIL | 0.469 FAIL | 1.00 PASS | 0.286 PASS | 19 |

No single symbol clears ALL 5 validators simultaneously full-sample: BTC/USDT
comes closest (4/5 pass, only fails max-drawdown at 36.1% vs 25% threshold --
a large single-position-sizing issue, not a signal-quality issue), but the
grid's promising 27.8% pass fraction (strong for this repo, and genuinely
spanning both asset classes and 2 of 3 vol regimes) does not translate into
a full-sample validator-clean config on any tested symbol.

## Verdict: REJECTED (near-miss, worth revisiting)

No symbol passes all 5 validators full-sample. Notably BTC/USDT is a
concrete near-miss (only MDD fails, decisively driven by unscaled 1.0x
exposure) -- a future iteration should try this exact MRAT z-score
construction on BTC/USDT with an explicit `leverage_cap` position-sizing
parameter (same rescue pattern already validated elsewhere in this repo,
e.g. 2026-09-15-021 OBV sizing dial) to try to bring MDD under 25% without
touching the entry/exit logic. Equity symbols (QQQ/SPY) fail more
fundamentally on Sharpe/TC/parameter-sensitivity and are less promising.
Strategy file kept in `strategies/` as this near-miss's record.
