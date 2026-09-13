# CMO Sizing + Deadband, Shortened Trend Window (retrofit from RVI fix) — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-083 | **Outcome:** ACCEPTED — QQQ AND SPY both, all 5 validators; crypto decisively rejected

## Hypothesis
Direct follow-up to 2026-09-13-082's finding (shortened SMA trend-gate window ~40d lets a
continuous sizing overlay pass both QQQ and SPY) and its own recommendation to retrofit this
into other QQQ-only accepted sizing overlays. Applied here to CMO sizing (2026-09-13-078,
previously QQQ-only, SPY Sharpe near-miss 0.775 at trend_window=200). Sweep confirmed SPY
Sharpe rises to ~1.01-1.08 at trend_window 30-40 while QQQ stays ≥1.0.

## Grid test (Step 6)
`scripts/run_grid_cmo_shorttrend.py`, param_grid: trend_window∈{30,40,50}, deadband∈{0.10,0.15},
cmo_sensitivity∈{0.4,0.6}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3.
2017-01-01 to 2026-09-01.

- total_cells=144, passed=40, **pass_fraction=0.278**
- by_asset_class: equity 40/72; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 24/48, mid 16/48, **high 0/48**
- best_cell: QQQ, trend_window=50, deadband=0.10, cmo_sensitivity=0.4, low-vol, Sharpe=2.45

## Single-config validation (Step 7) — config trend_window=40, deadband=0.10, cmo_sensitivity=0.4

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.020 | **PASS** 1.081 |
| Max Drawdown (<0.25) | PASS 0.231 (near ceiling) | PASS 0.128 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | PASS 0.778 (186 trades) | PASS 0.794 (161 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.050 | PASS 0.059 |

## Decision: ACCEPTED for both QQQ and SPY — all 5 validators pass on both symbols. Second
dual-symbol full accept this cron trigger (after RVI-082), confirming the shortened
trend-window fix generalizes across different sizing-dial indicators, not just RVI. QQQ's MDD
(0.231) is closer to the 0.25 ceiling than the trend_window=200 CMO variant's 0.211 — a
trade-off worth monitoring if extended further. Crypto decisively rejected (0/72, unaffected).

## Note for future iterations
Two-for-two on "retrofit shortened trend_window" producing dual-symbol accepts (RVI-082,
CMO-083). Worth continuing the retrofit sweep on the remaining QQQ-only accepted sizing
overlays (%B-071, Aroon-072, Williams %R-074, UO-079, StochRSI-080) in future iterations.
