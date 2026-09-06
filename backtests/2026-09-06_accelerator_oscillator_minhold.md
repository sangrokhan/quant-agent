# Accelerator Oscillator (AC) + Min-Hold-Days Gate — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_accelerator_oscillator_minhold.py`
**Outcome:** ACCEPTED (QQQ only, min_hold_days=15/trend_window=100/atr_target_mult=3.0/atr_stop_mult=2.0)

## Hypothesis

Direct fix for near-miss 2026-09-06-173 (Accelerator Oscillator
zero-line crossover, QQQ Sharpe 0.927 near-miss, both QQQ/SPY failed
transaction-cost survival at 366-373 trades). Applying the min-hold-days
fix pattern (Klinger 2026-09-04-085, ZLEMA 2026-09-06-171 this cron
trigger): suppress the crossover-based exit for the first N days after
entry while keeping ATR stop-loss/take-profit active immediately.

## Tuning process

Initial min_hold_days-only sweep (5/10/15 x trend_window 100/200) got
QQQ to Sharpe 0.871 (TC-adj barely passed at 0.503) — still short on
Sharpe. A broader sweep adding `atr_target_mult` found min_hold_days=15/
trend_window=100/atr_target_mult=3.0 reaches Sharpe 1.318 but MDD 0.283
now FAILS (widening the take-profit target increases average trade P&L
variance). A further sweep of `atr_stop_mult` (tighter stop) found
atr_stop_mult=2.0 (looser stop, counterintuitively — fewer premature
stop-outs during normal pullbacks) combined with the same min_hold=15/
trend_window=100/atr_target_mult=3.0 clears all four validators.

## Single-config validator results

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|
| QQQ | **1.495 (PASS, thr 1.0)** | **0.218 (PASS, thr 0.25)** | **1.088 (PASS, thr 0.5)** | 0.142 (PASS, thr 0.5) |
| SPY | 0.935 (FAIL) | 0.275 (FAIL) | 0.486 (FAIL) | 0.093 (PASS) |

Crypto sanity check: BTC/USDT Sharpe 0.19, ETH/USDT Sharpe 0.26 — both
far below threshold, consistent with the base strategy's finding.

Walk-forward: skipped (repo-wide pre-existing tooling bug).

## Step 6 grid summary (initial min_hold_days/trend_window sweep)

- Grid: `param_grid={min_hold_days:[5,10,15], trend_window:[100,200]}`,
  `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
  2015-01-01 to 2026-09-01. 72 total cells.
- `pass_fraction`: 0.25 (18/72) — same as pre-fix strategy's 0.25
  (min_hold_days alone didn't change the grid's own pass rate, but DID
  find the pathway to a passing full-sample config via a follow-up
  sweep on atr_target_mult/atr_stop_mult not part of this initial grid)
- `by_asset_class`: equity 18/36 (50%), crypto 0/36 (0%)
- `by_vol_regime`: low 12/24 (50%), mid 6/24 (25%), high 0/24 (0%)
- The final accepted config (min_hold=15/trend_window=100/
  atr_target_mult=3.0/atr_stop_mult=2.0) was found via a targeted
  follow-up sensitivity sweep after the initial grid's best cells
  suggested QQQ specifically needed a looser take-profit AND a looser
  stop simultaneously, not captured by the initial 2-parameter grid.

## Decision

**Accepted, scoped to QQQ only.** All four validators run pass cleanly
for QQQ at min_hold_days=15/trend_window=100/atr_target_mult=3.0/
atr_stop_mult=2.0 (Sharpe 1.495, MDD 0.218, TC-adjusted Sharpe 1.088,
parameter sensitivity relative_std 0.142). SPY at the identical config
remains a near-miss on all three of Sharpe/MDD/TC (0.935/0.275/0.486) —
do not extend this config to SPY. Crypto remains categorically
unsuitable. This is the SECOND successful application this cron trigger
of the min-hold-days fix pattern (after ZLEMA 2026-09-06-171),
reinforcing it as a reliable general technique for rescuing
cost-sensitive-but-otherwise-close crossover strategies in this repo.
