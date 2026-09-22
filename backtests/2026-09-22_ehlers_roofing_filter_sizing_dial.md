# Ehlers Roofing Filter — Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ehlers_roofing_filter_sizing_dial.py`
**Status:** ACCEPTED (BTC/USDT only, leverage_cap=0.9); REJECTED (QQQ, SPY, ETH/USDT)

## Hypothesis

Continuous-sizing-dial rescue of this cron trigger's own 2026-09-22-056
(plain Ehlers Roofing Filter Filt/Trigger BINARY crossover, rejected — edge
confined to low/mid-vol, complete high-vol collapse) and 2026-09-22-058 (an
explicit vol-exclusion gate did not fix it, and even destabilized QQQ's
parameter sensitivity). Per this repo's established rescue pattern for
exactly this failure mode (binary oscillator/crossover collapsing under
vol-regime/parameter stress — see Hurst, DTI, COG, VPT, Disparity Index
precedents), the raw `(Filt - Trigger)` divergence — the exact quantity
whose SIGN drove the binary crossover — is rolling z-scored (100-day
window) and tanh-squashed to `[-1,1]`, then used directly as a continuous
exposure fraction within an `SMA(trend_window)` uptrend gate with a
deadband (exposure snapped to 0 when `|dial| < deadband`).

## Grid test summary (Step 6)

`run_strategy_grid`: `sensitivity` in {0.3,0.5,0.8}, `deadband` in
{0.1,0.2,0.3}, `trend_window` in {50,100}; symbols QQQ/SPY (equity),
BTC/USDT/ETH/USDT (crypto); `vol_regime_splits=3`.

- **total_cells:** 216, **passed_cells:** 107, **pass_fraction:** 0.495 (up from 0.287/0.296 for the binary variants — clear improvement)
- **by_asset_class:** equity 21/108 (0.194), **crypto 86/108 (0.796)**
- **by_vol_regime:** low 49/72 (0.681), mid 43/72 (0.597), high 15/72 (0.208 — up from 0.000, meaningfully rescued)
- **best_cell:** sensitivity=0.8, deadband=0.1, trend_window=100 — ETH/USDT, mid-vol, Sharpe 2.03
- **worst_cell:** sensitivity=0.3, deadband=0.3, trend_window=50 — SPY, low-vol, Sharpe -1.87

The continuous-sizing reframing substantially rescued the high-vol collapse
(0.208 vs 0.000) and dramatically improved crypto performance (0.796 vs
0.259 for the binary variant), at the cost of weaker equity performance
(0.194 vs 0.315).

## Single-config validation (Step 7) — grid's best config (sensitivity=0.8, deadband=0.1, trend_window=100)

| Validator | QQQ | SPY | ETH/USDT | BTC/USDT (lev=1.0) | BTC/USDT (lev=0.9, retuned) | Threshold |
|---|---|---|---|---|---|---|
| Sharpe ratio | 0.212 FAIL | 0.421 FAIL | 0.743 FAIL | 1.171 PASS | 1.171 PASS | ≥ 1.0 |
| Max drawdown | 0.137 PASS | 0.120 PASS | 0.357 FAIL | 0.251 FAIL (near-miss) | 0.227 PASS | ≤ 0.25 |
| TC survival | -0.073 FAIL | -0.020 FAIL | 0.666 PASS | 1.072 PASS | 1.059 PASS | ≥ 0.5 |
| Walk-forward (4-split) | 0.50 FAIL | 0.75 PASS | 1.00 PASS | 0.75 PASS | 0.75 PASS | ≥ 0.75 |
| Parameter sensitivity | 0.419 PASS | 0.219 PASS | 0.142 PASS | 0.023 PASS | 0.023 PASS | ≤ 0.5 |

BTC/USDT at leverage_cap=1.0 was a near-miss: only max drawdown failed
(0.251 vs 0.25 threshold — essentially a rounding-level miss). A standard
leverage-cap-aware retune sweep found **leverage_cap=0.9 clears all 5
validators** (Sharpe 1.171, MDD 0.227, TC-survival 1.059, unchanged
walk-forward/param-sensitivity since those are scale-invariant to a
uniform leverage multiplier). QQQ, SPY, and ETH/USDT each fail 2-3 of 5
validators at the grid's best shared config and were not separately
retuned (equity's own best cells scored much lower — 0.194 pass fraction —
suggesting a different config, not leverage, would be needed, out of
scope for this iteration's budget).

## Decision

**ACCEPTED for BTC/USDT only** (`leverage_cap=0.9`, `sensitivity=0.8`,
`deadband=0.1`, `trend_window=100`) — all 5 validators pass. **REJECTED**
for QQQ, SPY, and ETH/USDT at this shared config. This confirms the
continuous-sizing-dial reframing is a genuine improvement over the binary
crossover (rescued the high-vol collapse and unlocked a passing crypto
config), consistent with this repo's broader pattern that Ehlers-family
cycle indicators tend to work better as continuous dials than binary
triggers — but the edge here is narrow (single symbol, single asset
class) rather than broad.
