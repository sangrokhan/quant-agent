# 2026-09-22 — Wyckoff Phase C Test (Spring + lower-volume retest)

**Hypothesis**: Source: https://algobars.com/strategy-templates/wyckoff-complete/wyckoff-phase-c-test/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Two-stage mechanic distinct from this repo's prior
single-stage Wyckoff Spring entries: (1) a Spring event (price pierces
below a trading-range low and reverses back inside), followed by (2) a
later "test" bar that revisits the Spring low on volume notably LESS than
the Spring bar's own volume ("supply exhausted"), confirmed by a bullish
reversal candle. Stop placed below the ORIGINAL Spring low (not the test
low); target at the top of the trading range.

**Strategy file**: `strategies/2026-09-22_wyckoff_phase_c_test.py`

**Grid test** (`run_grid_wyckoff_phase_c_test.py`): param_grid =
`{range_width_pct: [0.12, 0.20], test_volume_ratio: [0.5, 0.7, 0.9]}`,
symbols = equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=72, passed_cells=0, pass_fraction=0.0
- by_asset_class: equity 0/36, crypto 0/36
- by_vol_regime: low 0/24, mid 0/24, high 0/24
- best_cell: SPY mid-vol, Sharpe 0.758 (near-miss, per-tercile, still below
  threshold)
- worst_cell: QQQ high-vol, Sharpe -1.233

**Trade frequency note**: Equity signal is extremely sparse by construction
(QQQ 1-5 entries over the full 2015-2026 sample across the params tested,
SPY 3-5 entries) -- the Spring+lower-volume-retest+bullish-reversal
conjunction is a genuinely rare pattern on daily equity bars, consistent
with the source's own framing as "the lowest-risk entry in the entire
accumulation structure" (implying rarity/selectivity by design). Crypto has
much higher signal frequency (76-95 entries) but the edge is still absent
after evaluation.

**Decision**: REJECTED (all symbols, all tested configs). 0/72 grid cells
passed both Sharpe and MDD thresholds simultaneously in any
asset-class/vol-regime/parameter combination. Equity trade counts are too
sparse for statistical confidence even where isolated cells looked
directionally positive; crypto has adequate trade counts but no edge
materializes. No further validators run given the decisive 0/72 grid
result (consistent with RESEARCH_LOOP.md Step 7 guidance -- a 0.0
pass_fraction across the full grid is conclusive without a separate
single-config validator pass).
