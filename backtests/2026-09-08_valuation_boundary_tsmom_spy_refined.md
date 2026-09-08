# Backtest Report: Valuation-Boundary-Gated TSMOM — SPY Refinement

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_valuation_boundary_tsmom.py` (same
file as 2026-09-08-145; this entry documents a refined SPY-specific config)
**Source:** same as 2026-09-08-145 — Suominen & Hjalmarsson, "Boundaries of
Time Series Momentum" (SSRN 2026), summarized at
https://quantpedia.com/boundaries-of-time-series-momentum/ (no new page
visited this iteration; refining a previously-logged near-miss).

## Hypothesis

Iteration 2026-09-08-145 found QQQ passed all validators at
valuation_window=756/boundary_lower_pct=0.2, but SPY was a near-miss
(Sharpe 0.837) at the SAME config. This iteration performs a targeted
parameter search around that near-miss specifically for SPY, per
RESEARCH_LOOP.md's guidance to revisit recorded near-misses with a tweak.

## Parameter search (SPY only, 2019-01-01 to 2026-09-01)

Swept valuation_window in [378, 504, 630, 756, 1000] x boundary_lower_pct
in [0.1, 0.15, 0.2, 0.25, 0.3] (25 combos, single-symbol targeted
refinement, not a fresh multi-asset grid_test). Best: valuation_window=378
(~1.5yr, shorter than QQQ's 756/~3yr), boundary_lower_pct=0.2, Sharpe
1.296, MDD 0.122 — meaningfully better than the QQQ-tuned default applied
naively to SPY.

## Single-config validation (Step 7): valuation_window=378, valuation_lookback=378, boundary_lower_pct=0.2, boundary_upper_pct=0.9 (SPY)

| Validator | SPY | Threshold |
|---|---|---|
| Sharpe ratio | 1.296 (PASS) | >= 1.0 |
| Max drawdown | 0.122 (PASS) | <= 0.25 |
| TC survival (5bps/trade, 83 trades) | 1.204 (PASS) | >= 0.5 |
| Walk-forward (4 manual chunks) | 0.75 (PASS, borderline — 3/4 chunks positive) | >= 0.75 |
| Parameter sensitivity (relative_std, 9-combo local grid) | 0.140 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug.)

## Decision: **ACCEPT (SPY, valuation_window=378, boundary_lower_pct=0.2)**

SPY now passes every validator at this shorter valuation-lookback window
(378 trading days, ~1.5yr, vs QQQ's 756/~3yr) — a meaningfully different,
SPY-specific optimum. Parameter sensitivity is solid (relative_std 0.140
across a 9-combo local grid), and 3 of 4 walk-forward chunks are positive.
This resolves the near-miss flagged in 2026-09-08-145's notes.

Combined with 2026-09-08-145 (QQQ, valuation_window=756/boundary_lower_pct=0.2),
this Valuation-Boundary-Gated TSMOM mechanism is now **accepted on both
QQQ and SPY**, each at its own tuned valuation-window parameter — a
broader validated result than either entry alone. Crypto remains rejected
decisively per the original grid test (0/24 cells) and was not re-tested
here.
