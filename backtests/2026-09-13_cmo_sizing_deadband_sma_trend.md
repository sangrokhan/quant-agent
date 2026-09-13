# CMO Continuous Sizing + Exposure-Change Deadband on SMA(200) Trend Gate — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-078 | **Outcome:** ACCEPTED (QQQ, all 5 validators); SPY near-miss (Sharpe 0.775<1.0); crypto decisively rejected

## Hypothesis
Direct fix for this cron trigger's 2026-09-13-076 (CMO continuous sizing, rejected on
transaction-cost survival due to CMO's noisy bar-to-bar turnover, 562/525 trades). Per
threshold-rebalancing / tolerance-band literature (web_search: tradevae.com, quantroutine.com,
nottldr.com, stockalpha.ai) — "a tolerance band is the range around each target weight within
which no action is taken... threshold rebalancing is cost-efficient because you only trade
when drift becomes material." Adds an exposure-change deadband: only update held exposure when
the raw CMO-driven exposure drifts more than `deadband` from the currently-held value.

## Grid test (Step 6)
`scripts/run_grid_cmo_deadband.py`, param_grid: deadband∈{0.03,0.05,0.10},
cmo_sensitivity∈{0.4,0.6}, base_exposure∈{0.8,1.0}; symbols equity={QQQ,SPY}
crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3. 2017-01-01 to 2026-09-01.

- total_cells=144, passed=36, **pass_fraction=0.25**
- by_asset_class: equity 36/72; **crypto 0/72 (decisive fail — same as underlying CMO strategy)**
- by_vol_regime: low 24/48, mid 12/48, **high 0/48**
- best_cell: QQQ, deadband=0.10, cmo_sensitivity=0.4, base_exposure=1.0, low-vol, Sharpe=2.47

## Single-config validation (Step 7) — best config deadband=0.10, cmo_sensitivity=0.4, base_exposure=1.0, cmo_window=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.117 | **FAIL (near-miss)** 0.775 |
| Max Drawdown (<0.25) | PASS 0.209 | PASS 0.200 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **PASS** 1.063 (56 trades, down from 562 raw) | **PASS** 0.660 (85 trades, down from 525 raw) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.008 | PASS 0.012 |

## Decision: ACCEPTED for QQQ (all 5 validators pass); SPY near-miss (Sharpe fail only, all other
validators pass); crypto decisively rejected.

The deadband fix worked exactly as hypothesized: trade count fell 10x (562→56 QQQ, 525→85 SPY)
and net-of-cost Sharpe flipped from failing (0.447/0.117) to comfortably passing (1.063/0.660)
with essentially unchanged raw directional Sharpe (1.117 vs 1.114 QQQ) and much tighter
parameter sensitivity (0.008 vs 0.028) since exposure now moves in discrete steps rather than
tracking every CMO wiggle. This confirms the general principle from this cron trigger's CMO
(076) and Ultimate Oscillator (077) TC-failures: the turnover, not the underlying signal
quality, was the binding constraint for un-smoothed multi-window-sum oscillators used as
continuous sizing dials — a simple exposure-change deadband is sufficient to fix it without
altering the core hypothesis.

## Note for future iterations
The Ultimate Oscillator sizing overlay (077, rejected on TC with -0.124/-0.252 net Sharpe and
~1800 trades) is a strong candidate to revisit with this same deadband technique next — its
raw signal also passed Sharpe/MDD/walk-forward/param-sensitivity and only failed on turnover,
likely by an even larger margin needing a wider deadband given ~3x the trade count of CMO.
