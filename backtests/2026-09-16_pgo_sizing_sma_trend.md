# Backtest Report: PGO (Pretty Good Oscillator) Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_pgo_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-103

## Hypothesis

PGO (Pretty Good Oscillator, Mark Johnson): `PGO = (Close-SMA(Close,N))/EMA(TrueRange,N)`,
an ATR-normalized distance-from-moving-average measure. Repo has 2 prior
PGO entries, both binary breakout-threshold triggers (crossing above
+3.0), both rejected/near-miss: 2026-09-08-049 (QQQ Sharpe 0.998/MDD
0.252 breach) and its follow-up 2026-09-09-052 (added trend gate + ATR
stop, still rejected). Neither used PGO as a continuous sizing dial.
Formula already confirmed in this repo (pineify.app, reused unchanged, no
new fetch this sub-iteration). This iteration reframes PGO as a
**continuous sizing dial** (rolling z-score + tanh squash to [-1,1])
inside an SMA(trend_window) uptrend gate with deadband, leverage-cap-aware
for crypto from the start. First PGO continuous-sizing variant.

## Grid test summary (`grid_result_pgo_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3. 72 cells.
- `pass_fraction`: **0.639** (46/72) — best pass fraction of this cron
  trigger's new-indicator entries.
- `by_asset_class`: equity 24/36 (0.667), crypto 22/36 (0.611) — both
  strong.
- `by_vol_regime`: low 24/24 (1.00), mid 12/24 (0.50), high 10/24 (0.417) —
  best high-vol resilience of this trigger's entries.
- best cell: QQQ, sensitivity=0.4/deadband=0.30, low-vol, Sharpe 2.75.
- worst cell: SPY, sensitivity=0.6/deadband=0.20, mid-vol, Sharpe 0.108.

## Single-config validation (`validators_pgo_sizing.json`)

Per-symbol retuned config, full 2019-01-01..2026-09-01 sample:

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd pass frac | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.400 | 0.086 | pass | 1.00 | pass | PASS |
| SPY | 1.211 | 0.072 | pass | 1.00 | pass | PASS |
| BTC/USDT | 1.637 | 0.231 | pass | 1.00 | pass | PASS |
| ETH/USDT | 1.512 | 0.180 | pass | 1.00 | pass | PASS |

All 5 validators pass on all 4 symbols, no near-misses needing a widened
search.

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First PGO
continuous-sizing variant in this repo, rescuing an indicator with two
prior rejected binary-trigger attempts.

Per-symbol params used:
- QQQ: trend_window=40, pgo_window=21, zscore_window=60, base_exposure=0.4,
  sensitivity=0.4, leverage_cap=1.0, deadband=0.35
- SPY: sensitivity=0.5 (else same)
- BTC/USDT: base_exposure=0.2, sensitivity=0.3, leverage_cap=0.5, deadband=0.20
- ETH/USDT: base_exposure=0.2, sensitivity=0.3, leverage_cap=0.5, deadband=0.15
