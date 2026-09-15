# Hurst Exponent Continuous Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_hurst_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-156

## Hypothesis
Direct fix attempt for prior rejected binary-threshold Hurst regime filters
(2026-09-04-155/156, 2026-09-12-136). Reframes the repo's existing R/S
Hurst estimator as a CONTINUOUS SIZING dial ((H-0.5)*2 rescaled to ~[-1,1])
inside an SMA(trend_window) uptrend gate with deadband, instead of a hard
binary H>threshold gate. Source: https://stratcraft.ai/indicators/hurst/
(re-confirms formula H=log(R/S)/log(n); H>0.5 persistence/trending) plus
this repo's existing FractalCycles-sourced R/S implementation
(strategies/2026-09-04_hurst_regime_ema_crossover.py, unchanged).

## Grid test (trend_window x hurst_window x sensitivity x deadband, 3 vol
regimes, QQQ/SPY/BTC-USDT/ETH-USDT)
- total_cells: 288, passed: 148, pass_fraction: 0.514
- by_asset_class: equity 86/144 (0.597), crypto 62/144 (0.431)
- by_vol_regime: low 85/96 (0.885), mid 63/96 (0.656), high 0/96 (0.0) --
  strategy decisively fails in high-vol regimes across the board
- best_cell: ETH/USDT mid-vol, trend_window=50/hurst_window=80/sens=0.4/
  deadband=0.15, Sharpe 2.64 (cell-level, not full-sample)

## Single-config validator results (per-symbol tuned config)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param-sens | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | tw=40,hw=100,sens=0.5,db=0.20,lev=1.0 | 0.989 (FAIL, <1.0) | 0.140 (PASS) | net Sharpe 0.406 (FAIL, <0.5) | 1.0 (PASS) | 0.048 (PASS) | REJECT (Sharpe + TC near-miss) |
| SPY | tw=40,hw=100,sens=0.5,db=0.20,lev=1.0 | 1.207 (PASS) | 0.073 (PASS) | net Sharpe 0.513 (PASS) | 1.0 (PASS) | 0.089 (PASS) | ACCEPT (all 5 pass) |
| BTC/USDT | tw=50,hw=80,sens=0.4,db=0.15,lev=0.5 | 0.170 (FAIL) | 0.314 (FAIL) | net Sharpe -0.051 (FAIL), 6414 trades | 1.0 (PASS) | 0.113 (PASS) | REJECT (decisive) |
| ETH/USDT | tw=50,hw=80,sens=0.4,db=0.15,lev=0.5 | 0.174 (FAIL) | 0.377 (FAIL) | net Sharpe -0.046 (FAIL), 6546 trades | 1.0 (PASS) | 0.213 (PASS) | REJECT (decisive) |

## Decision
**Accept SPY only** (config tw=40,hw=100,sensitivity=0.5,deadband=0.20,
leverage_cap=1.0, all 5 validators pass). QQQ near-misses on Sharpe (0.989
vs 1.0 threshold) and TC-survival -- a plausible follow-up sub-iteration
could widen the deadband/trend_window for QQQ specifically. Crypto
decisively rejected: the Hurst R/S estimator, recomputed every 5 bars and
forward-filled, still produces >6000 trades over the crypto sample even
with a 0.15 deadband -- the rolling-window R/S statistic is simply too
noisy bar-to-bar for high-frequency crypto data at this deadband setting,
and MDD also breaches the 0.25 threshold despite the 0.5x leverage cap.
