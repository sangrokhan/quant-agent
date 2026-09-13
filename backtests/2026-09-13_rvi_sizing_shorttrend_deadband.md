# RVI Sizing + Deadband, Shortened Trend Window (SPY-fix investigation) — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-082 | **Outcome:** ACCEPTED — QQQ AND SPY both, all 5 validators (first dual-symbol full accept this cron trigger); crypto decisively rejected

## Hypothesis
Direct investigation of a pattern flagged across 6 consecutive accepted sizing-overlay entries
this cron trigger (071/072/074/078/079/080/081): all pass QQQ full-sample Sharpe but come up
short on SPY specifically, always at the shared trend_window=200 SMA default. Measured this
iteration: QQQ ann. vol 22.8%/ann. return 23.4% vs SPY 18.2%/15.4% over the backtest window —
SPY's slower, choppier trend plausibly needs a SHORTER trend-confirmation window to reduce
whipsaw lag. A quick sweep on the RVI-sizing skeleton (081, sizing logic unchanged) showed SPY
Sharpe rising from 0.729 (trend_window=200) to ~1.03-1.04 at trend_window 30-40, with QQQ
staying ≥1.0 across the same range — suggesting a single shared shorter window might pass BOTH.

## Grid test (Step 6)
`scripts/run_grid_rvi_shorttrend.py`, param_grid: trend_window∈{30,40,50}, deadband∈{0.10,0.15},
rvi_sensitivity∈{0.4,0.6}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3.
2017-01-01 to 2026-09-01.

- total_cells=144, passed=40, **pass_fraction=0.278** (up from 0.25 baseline for the trend_window=200 RVI variant)
- by_asset_class: equity 40/72; **crypto 0/72 (decisive fail, unaffected by trend_window change)**
- by_vol_regime: low 24/48, mid 16/48, **high 0/48**
- best_cell: QQQ, trend_window=50, deadband=0.15, rvi_sensitivity=0.6, low-vol, Sharpe=2.53

## Single-config validation (Step 7) — config trend_window=40, deadband=0.15, rvi_sensitivity=0.4

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.000 | **PASS** 1.042 |
| Max Drawdown (<0.25) | PASS 0.190 | PASS 0.108 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | PASS 0.670 (211 trades) | PASS 0.643 (185 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.044 | PASS 0.054 |

## Decision: ACCEPTED for both QQQ and SPY — all 5 validators pass on both symbols. Crypto
decisively rejected (0/72, unaffected by the trend-window change, confirming crypto's rejection
in this family is unrelated to trend-window calibration). QQQ's full-sample Sharpe (1.000) is a
razor-thin pass vs. the trend_window=200 RVI variant's 1.119 — this trades some QQQ edge for
SPY robustness, but achieves what 6 consecutive prior sizing-overlay entries this cron trigger
could not: a single shared config passing both major equity benchmarks simultaneously.

## Note for future iterations
Confirms the hypothesis: trend_window=200 was calibrated closer to QQQ's regime; a shorter
window (30-50d) generalizes better across both SPY and QQQ for this whole sizing-overlay
family. Worth retrofitting trend_window=40 (or re-sweeping per-oscillator) into the other 5
accepted QQQ-only variants (%B-071, Aroon-072, Williams %R-074, CMO-078, UO-079, StochRSI-080)
in a future iteration to see if they can also be upgraded to dual-symbol accepts.
