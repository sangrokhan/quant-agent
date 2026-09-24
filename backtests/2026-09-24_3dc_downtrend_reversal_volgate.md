# Backtest report: 3DC with volatility-regime gate + capped stop-loss

**Strategy file:** `strategies/2026-09-24_3dc_downtrend_reversal_volgate.py`
**Hypothesis source:** https://thepatternsite.com/3DC.html (Thomas Bulkowski's write-up of Andrea Unger's "The Trend Compression Pattern," TASC Feb 2024)

## Hypothesis

Direct fix attempt for this same cron trigger's own recorded near-miss
(2026-09-24-125): the base 3DC downtrend-reversal strategy failed on max
drawdown (0.287 SPY / 0.381 QQQ) and parameter sensitivity (relative std
1.023 SPY / 1.540 QQQ), with that entry's own notes suggesting "an added
volatility-regime gate or tighter stop-loss to control drawdown." This
variant adds both: (1) a realized-vol regime gate (flatten/no new entries
when trailing 20d vol exceeds `vol_regime_ratio` x its own trailing
252d median — same pattern as `2026-09-03_bb_meanrev_qqq_volregime.py`),
and (2) a capped stop-loss (tighter of the pattern-boundary stop or
`max_stop_pct` of entry price).

## Grid test summary (Step 6)

`param_grid`: max_stop_pct ∈ {0.03,0.05,0.08}, vol_regime_ratio ∈
{0.8,1.0,1.2}, target_mult ∈ {1.5,2.0}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to
2026-09-01.

- **total_cells:** 216, **passed_cells:** 48, **pass_fraction:** 0.222
- **by_asset_class:** equity 48/108, crypto **0/108** (vol gate essentially eliminates the already-weak crypto signal entirely)
- **by_vol_regime:** low 36/72, mid 12/72, high 0/72 (expected — the gate itself suppresses high-vol trading)
- **best_cell:** max_stop_pct=0.05, vol_regime_ratio=1.2, target_mult=2.0, QQQ low-vol, Sharpe=2.254
- Most robust config: vol_regime_ratio=1.2 with any max_stop_pct/target_mult combo (4/12 cells each).

## Single-config validation (Step 7) — SPY & QQQ, max_stop_pct=0.05, vol_regime_ratio=1.2, target_mult=1.5, full sample

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** 1.133 | **PASS** 1.322 | ≥ 1.0 |
| Max drawdown | **PASS** 0.197 | **PASS** 0.202 | ≤ 0.25 |
| Transaction cost survival | **PASS** 0.826 (107 trades) | **PASS** 1.052 (109 trades) | ≥ 0.5 |
| Walk-forward (4 splits) | **PASS** 1.0 | **PASS** 0.75 | ≥ 0.75 |
| Parameter sensitivity | **FAIL** relative std 0.722 | **FAIL** relative std 1.680 | ≤ 0.5 |

Both the max-drawdown fix (SPY: 0.287→0.197, QQQ: 0.381→0.202) and the
Sharpe improvement (SPY: 0.902→1.133, QQQ: 1.012→1.322) worked exactly as
the near-miss note predicted — 4 of 5 validators now PASS on both
symbols, a substantial improvement over the base strategy's 2-3
failures. Only parameter sensitivity remains a fail (relative std note:
this metric is computed by taking the last-seen vol-regime slice's Sharpe
per param combo in this repo's `check_parameter_sensitivity` helper
usage pattern — same methodology used elsewhere in this repo — so some
of the dispersion reflects cross-vol-regime Sharpe variation baked into
which grid cell happens to be picked per param combo, not purely
parameter fragility in the traditional sense).

## Decision (Step 8): REJECT

1 of 5 validators (parameter sensitivity) still fails on both symbols —
reject per Step 8's strict all-must-pass criterion, despite the
substantial improvement from the base 3DC strategy. This is a genuine
near-miss worth flagging for a further-tightened future revisit (e.g.
narrowing the target_mult/max_stop_pct grid around the winning region, or
using a stricter single-vol-regime-only parameter-sensitivity comparison)
rather than a decisive rejection — 4/5 validators now pass on both
symbols, and the drawdown/Sharpe fixes both worked as hypothesized.

Strategy/report/grid files are kept in the repo as a record of a rejected
(but substantially improved) attempt, and as a near-miss note for a
future loop.
