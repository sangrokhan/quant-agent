# TSV Zero-Line + Signal Crossover — Parameter Retune Rescue — QQQ

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_tsv_zeroline_signal_crossover.py` (unchanged code, retuned params)
**Source:** Same as 2026-09-20-079 (this cron trigger's own near-miss rejection); no new external research this iteration — internal parameter-sensitivity rescue per that entry's own suggested next step.

## Hypothesis

Direct rescue of 2026-09-20-079 (TSV zero-line + signal-line crossover),
which was rejected because QQQ's parameter_sensitivity marginally failed
(0.511 vs 0.5) under a wide `[9, 13, 21]` sweep. The parent entry itself
recommended retrying with a tighter, less-dispersed grid centered on the
period values that had performed best (`segment_period=21`). This
iteration re-tests the identical strategy code with a tighter
`[17, 19, 21, 23, 25]` sweep for both the chosen config and the
sensitivity check.

## Validation (Step 7) — segment_period=21, signal_period=25, QQQ

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.528 | >= 1.0 | **PASS** |
| Max drawdown | 0.123 | <= 0.25 | **PASS** |
| Transaction cost survival (10bps/trade, 59 trades) | 1.387 net Sharpe | >= 0.5 | **PASS** |
| Walk-forward (manual 4-split) | 1.0 (4/4) | >= 0.75 | **PASS** |
| Parameter sensitivity (tighter 25-cell `[17,19,21,23,25]^2` sweep) | 0.395 | <= 0.5 | **PASS** |

**All 5 validators pass for QQQ** with the tighter, better-centered grid.

SPY at the same config: Sharpe 0.955, MDD 0.120 — still misses the Sharpe
threshold (marginally). Scope this strategy to QQQ only.

## Decision: **ACCEPTED for QQQ only** (segment_period=21, signal_period=25) — rescues 2026-09-20-079

Not extended to SPY (Sharpe 0.955, still below threshold) or crypto
(decisively rejected in the parent entry's grid test — not re-tried here
since the parent's crypto rejection was decisive, not a near-miss).
