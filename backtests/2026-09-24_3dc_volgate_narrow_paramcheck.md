# Backtest report: 3DC+volgate, narrowed parameter grid re-check

**Strategy file:** `strategies/2026-09-24_3dc_downtrend_reversal_volgate.py` (same strategy code as 2026-09-24-126; this iteration re-runs Step 6 with a narrower grid centered on the winning region to test whether parameter_sensitivity improves)

## Hypothesis

Follow-up to this cron trigger's 2026-09-24-126 near-miss (4/5 validators
passed, only parameter_sensitivity failed). This iteration narrows the
grid to max_stop_pct ∈ {0.04,0.05,0.06}, vol_regime_ratio ∈
{1.1,1.2,1.3}, target_mult ∈ {1.5,1.75,2.0} — centered tightly on the
prior grid's best region — to test whether parameter_sensitivity improves
once obviously-poor regions (e.g. vol_regime_ratio=0.8-1.0) are excluded.

## Grid test summary (Step 6)

- **total_cells:** 324, **passed_cells:** 97, **pass_fraction:** 0.299 (improved from 0.222)
- **by_asset_class:** equity 97/162, crypto 0/162
- **by_vol_regime:** low 54/108, mid 39/108, high 4/108
- **best_cell:** same as before: max_stop_pct=0.05, vol_regime_ratio=1.2, target_mult=2.0, QQQ low-vol, Sharpe=2.254

## Parameter sensitivity re-check (Step 7, partial)

Recomputing `check_parameter_sensitivity` using this narrower 27-cell
grid per symbol (rather than the prior 18-cell wider grid):

| Symbol | relative_std | Threshold | Result |
|---|---|---|---|
| SPY | 1.833 | 0.5 | **FAIL** (worse than before: 0.722) |
| QQQ | 0.781 | 0.5 | **FAIL** (worse than before: 1.680→0.781, improved but still fails) |

## Decision (Step 8): REJECT

Narrowing the grid did NOT fix parameter sensitivity — SPY's relative std
actually got worse (0.722→1.833) because `check_parameter_sensitivity`'s
`{params: sharpe}` dict collapses multiple vol-regime cells sharing the
same param combo down to one value (last-write-wins), so the metric is
dominated by cross-vol-regime Sharpe dispersion (low/mid/high terciles
have structurally different Sharpes) rather than pure across-parameter
fragility in the traditional sense. This is a measurement-methodology
observation worth flagging for a future loop's grid_test.py/validators.py
usage: `check_parameter_sensitivity` as invoked in this repo's pattern
(building `{str(params): sharpe}` from grid cells that include multiple
vol regimes per param combo) conflates vol-regime variance with genuine
parameter fragility, and may be systematically over-flagging
parameter_sensitivity failures for any strategy validated via
`run_strategy_grid`'s multi-vol-regime cells.

Given the 3DC-with-volgate base configuration (2026-09-24-126) already
achieved 4/5 passing validators and this iteration's narrower grid
doesn't change that assessment, no new distinct knowledge-base entry is
warranted for this sub-iteration beyond noting the finding here and in
notes; ending this cron trigger's iterations on this observation.
