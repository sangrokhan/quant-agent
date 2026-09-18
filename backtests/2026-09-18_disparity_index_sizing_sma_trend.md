# Disparity Index Continuous Sizing Dial (SMA Trend Gate) — QQQ + ETH/USDT Accepted

**Date:** 2026-09-18
**Strategy file:** `strategies/2026-09-18_disparity_index_sizing_sma_trend.py`
**Source:** GoCharting Disparity Index docs (formula already on file in this
repo from prior entry 2026-09-06-140: `Disparity Index =
100*(close-SMA)/SMA`).

## Hypothesis

This repo's prior Disparity Index entry (2026-09-06-140) used a binary
extreme-threshold mean-reversion trigger and was rejected (near-miss
confined to QQQ's mid-vol tercile only). This iteration reframes Disparity
Index as a **continuous sizing dial**: rolling z-scored + tanh-squashed to
[-1,1], used as an exposure multiplier inside an SMA(trend_window) uptrend
gate + deadband — the pattern that has rescued many other binary
near-miss/narrow-regime indicators in this repo (VAMA, DPO, Hurst, VHF,
TII, RVI, MAMA-FAMA spread, Kalman slope, CBOE SKEW, VPT, McGinley
Dynamic, T3).

## Grid test (trend_window∈{40,60} × sensitivity∈{0.5,0.6,0.8} × leverage_cap∈{0.4,1.0}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- 144 cells, 87 passed (**60.4%**)
- by_asset_class: equity 43/72 (59.7%), crypto 44/72 (61.1%) — balanced
  across both asset classes, unusually strong for crypto
- by_vol_regime: low 41/48 (85.4%), mid 32/48 (66.7%), high 14/48 (29.2%)
- Best per-symbol average-Sharpe configs: QQQ/SPY/ETH/USDT all favor
  `trend_window=40, sensitivity=0.6, leverage_cap=0.4`; BTC/USDT favors
  `leverage_cap=0.4` too once MDD is accounted for (leverage_cap=1.0 was
  grid-best on raw Sharpe but fails single-config MDD).

## Single-config validators (full sample 2019-01-01–2026-09-01, deadband=0.35)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | tw=40/sens=0.6/lev=0.4 | 1.283 PASS | 6.9% PASS | 0.598 PASS | 0.75 PASS | 0.106 PASS |
| SPY | tw=40/sens=0.6/lev=0.4 | 1.086 PASS | 4.6% PASS | 0.353 **FAIL** | 1.0 PASS | 0.032 PASS |
| BTC/USDT | tw=60/sens=0.6/lev=0.4 | 1.328 PASS | 25.6% **FAIL** (near-miss) | 1.107 PASS | 1.0 PASS | 0.040 PASS |
| ETH/USDT | tw=40/sens=0.6/lev=0.4 | 1.211 PASS | 19.9% PASS | 1.054 PASS | 1.0 PASS | 0.081 PASS |

## Decision

- **QQQ: ACCEPT.** All 5 validators pass (`trend_window=40, sensitivity=0.6,
  leverage_cap=0.4, deadband=0.35, di_sma_window=14`).
- **ETH/USDT: ACCEPT.** All 5 validators pass (`trend_window=40,
  sensitivity=0.6, leverage_cap=0.4, deadband=0.35`).
- **SPY: REJECT (near-miss).** Fails only TC-survival (net Sharpe 0.353 vs
  0.5 threshold, 138 trades) — every other validator passes comfortably
  including param-sensitivity (relative std 3.2%, very stable). A wider
  deadband to cut turnover further would likely rescue this.
- **BTC/USDT: REJECT (razor-thin near-miss).** Fails only MDD (25.6% vs
  25%, just 0.6pp over) — Sharpe 1.328, TC-survival 1.107, walk-forward
  1.0, param-sensitivity 0.040 all pass comfortably. A slightly lower
  leverage_cap (e.g. 0.35) would likely clear this threshold.

This is this cron trigger's strongest multi-asset grid result (60.4% pass
fraction, balanced across equity and crypto) — a rare case where the same
underlying construction and near-identical parameters work reasonably well
on both asset classes, distinct from the pattern of "equity-only accepts,
crypto decisively rejected" seen in most other iterations this trigger.
