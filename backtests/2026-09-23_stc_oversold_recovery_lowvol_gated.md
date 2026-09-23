# Schaff Trend Cycle (STC) Oversold-Recovery, Low-Vol-Regime-Gated Rescue Attempt — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_stc_oversold_recovery_lowvol_gated.py`
**Outcome:** REJECTED (rescue attempt failed — made full-sample Sharpe worse, not better)

## Hypothesis

Direct low-vol-regime-gate rescue attempt for near-miss/reject
2026-09-23-055 (plain STC oversold-recovery, trend-gated, full-sample
Sharpe 0.558 QQQ / 0.600 SPY). That iteration's grid showed the strategy's
edge decisively concentrated in low/mid-vol terciles (high-vol 0/72 cells
passed). This variant adds the repo's established low-vol-regime gate
(20d realized vol <= vol_regime_ratio x trailing 252d median,
`strategies/2026-09-03_bb_meanrev_qqq_volregime.py` construction) directly
to the entry condition. No new external source — internal-KB rescue
attempt only.

## Grid summary (Step 6)

`param_grid={stc_entry_level:[20,25], vol_regime_ratio:[0.8,1.0,1.2],
max_hold_days:[15]}`, `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-2026, 72 cells.

- pass_fraction: 0.194 (14/72) — **lower** than the ungated version's 0.245
- by_asset_class: equity 10/36, crypto 4/36
- by_vol_regime: low 8/24, mid 6/24, high 0/24
- best_cell: SPY, stc_entry_level=20/vol_regime_ratio=1.2, low-vol tercile, Sharpe 1.70
- worst_cell: SPY, stc_entry_level=20/vol_regime_ratio=1.0, high-vol tercile, Sharpe -1.15

## Single-config full-sample Sharpe check (stc_entry_level=20, max_hold_days=15, trend_window=150)

| vol_regime_ratio | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| 0.8 | 0.606 | 0.428 |
| 1.0 | 0.293 | 0.343 |
| 1.2 | 0.746 | 0.549 |

All configs remain well below the 1.0 threshold and are **worse** than the
ungated baseline (0.558 QQQ / 0.600 SPY) — the low-vol gate reduces both
the number of trades and the compounding benefit of holding through
mid-vol regime edge (which the grid showed still had positive pass_fraction,
18/72), so restricting purely to low-vol throws away usable signal rather
than concentrating it.

## Decision (Step 8): REJECT

Rescue attempt failed — worse full-sample Sharpe on every tested
`vol_regime_ratio` value than the already-rejected ungated baseline. No
further rescue attempts planned for this hypothesis family this cron
trigger.
