# Williams %R Sizing, Shortened Trend Window (retrofit from RVI/CMO fix) — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-084 | **Outcome:** ACCEPTED — QQQ AND SPY both, all 5 validators, no deadband needed; crypto decisively rejected

## Hypothesis
Direct follow-up applying the twice-validated shortened-trend-window fix (RVI-082, CMO-083) to
Williams %R sizing (2026-09-13-074, previously QQQ-only accepted, SPY Sharpe near-miss 0.792 at
trend_window=200). Unlike CMO/UO/StochRSI, Williams %R's High/Low-range construction is smooth
enough that no exposure-change deadband is required even at the shorter window.

## Grid test (Step 6)
`scripts/run_grid_williams_shorttrend.py`, param_grid: trend_window∈{30,40,50}, williams_window∈{10,14},
wr_sensitivity∈{0.4,0.6}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3.
2017-01-01 to 2026-09-01.

- total_cells=144, passed=40, **pass_fraction=0.278**
- by_asset_class: equity 40/72; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 24/48, mid 16/48, **high 0/48**
- best_cell: QQQ, trend_window=50, williams_window=10, wr_sensitivity=0.4, low-vol, Sharpe=2.45

## Single-config validation (Step 7) — config trend_window=40, williams_window=10, wr_sensitivity=0.6

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.023 | **PASS** 1.078 |
| Max Drawdown (<0.25) | PASS 0.232 (near ceiling) | PASS 0.133 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | PASS 0.783 (186 trades, no deadband needed) | PASS 0.794 (161 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.047 | PASS 0.059 |

## Decision: ACCEPTED for both QQQ and SPY — all 5 validators pass on both symbols, without
needing the deadband mechanism required for CMO/UO/StochRSI at this shortened window. Third
consecutive dual-symbol full accept this cron trigger (after RVI-082, CMO-083), confirming the
shortened-trend-window fix generalizes robustly. QQQ MDD (0.232) again sits near the 0.25
ceiling, a recurring trade-off of the shorter window across all three retrofits so far. Crypto
decisively rejected (0/72, unaffected).

## Note for future iterations
Three-for-three on the shortened-trend-window retrofit (RVI, CMO, Williams %R all become
dual-symbol accepts). Remaining untried retrofits: %B-071, Aroon-072, UO-079, StochRSI-080.
Also worth investigating: QQQ's MDD consistently landing near 0.25 at trend_window=40 across
all three retrofits suggests this may be close to the practical floor for this shortened-window
approach on QQQ specifically -- a future iteration could test whether MDD-focused tweaks (e.g.
a lower leverage_cap or an added vol-scaling term) buy back some margin.
