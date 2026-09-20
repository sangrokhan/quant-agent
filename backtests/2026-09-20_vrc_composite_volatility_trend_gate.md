# Backtest Report: VRC Composite Volatility Trend Gate

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_vrc_composite_volatility_trend_gate.py`
**KB id:** 2026-09-20-094

## Hypothesis

Per TrendSpider's Volatility Regime Classifier (VRC) product page (read via
browser_exec Google SERP/AI-overview + multiple store-page listings this
iteration): a composite of three volatility estimators -- Parkinson (20%
weight), Garman-Klass (30% weight), Yang-Zhang (50% weight) -- with the
highest weight on Yang-Zhang because it uniquely incorporates the overnight
gap component. This repo has tested each of Parkinson, Garman-Klass, and
Yang-Zhang individually as standalone regime gates; the TrendSpider weighted
composite is a novel, untested combination. Hypothesis: gating an SMA
crossover trend-follow entry to only fire when the composite's rolling
Z-score is in a "calm" (below-threshold) regime should produce a cleaner
split than any single estimator, since the composite averages out
estimator-specific noise.

## Grid test summary (fast_window x [10,20,30], slow_window x [50,100],
z_upper_bound x [0.5,1.0,1.5]; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- Total cells: 216, passed: 53, pass_fraction: 0.245
- By asset class: equity 39/108 (0.361), crypto 14/108 (0.130)
- By vol regime: low 33/72 (0.458), mid 16/72 (0.222), high 4/72 (0.056)
- Best cell: equity QQQ, fast_window=30/slow_window=100/z_upper_bound=1.5,
  low-vol tercile, Sharpe 2.198
- Worst cell: crypto BTC/USDT, fast_window=10/slow_window=100/z_upper_bound=1.5,
  mid-vol tercile, Sharpe -1.218

## Full-sample single-config scan (4 promising grid configs x 4 symbols)

| Symbol | fast_window | slow_window | z_upper_bound | Full-sample Sharpe |
|---|---|---|---|---|
| QQQ | 30 | 100 | 1.5 | 0.639 |
| QQQ | 20 | 50 | 1.0 | **0.686** (best QQQ) |
| QQQ | 30 | 100 | 1.0 | 0.634 |
| QQQ | 20 | 100 | 1.5 | 0.322 |
| SPY | 30 | 100 | 1.5 | 0.187 |
| SPY | 20 | 50 | 1.0 | 0.263 |
| SPY | 30 | 100 | 1.0 | 0.310 |
| SPY | 20 | 100 | 1.5 | 0.033 |
| BTC/USDT | 30 | 100 | 1.5 | -0.040 |
| BTC/USDT | 20 | 50 | 1.0 | 0.070 |
| BTC/USDT | 30 | 100 | 1.0 | -0.077 |
| BTC/USDT | 20 | 100 | 1.5 | 0.001 |
| ETH/USDT | 30 | 100 | 1.5 | 0.046 |
| ETH/USDT | 20 | 50 | 1.0 | 0.023 |
| ETH/USDT | 30 | 100 | 1.0 | 0.015 |
| ETH/USDT | 20 | 100 | 1.5 | 0.028 |

Crypto shows essentially no edge at all (Sharpe ~0), consistent with a
"calm regime gate" providing little benefit when trend-following itself is
weak on BTC/ETH with a slow SMA crossover base rule. Best equity full-sample
config (QQQ, fast=20/slow=50/z<=1.0) reaches only 0.686, well below the 1.0
threshold.

## Single-config validator (best QQQ config)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **FAIL** | value=0.686, threshold=1.0 |

Remaining validators skipped -- decisive Sharpe failure on the best
full-sample config makes accept impossible regardless.

## Decision: REJECTED

The TrendSpider-weighted composite VRC gate does not outperform the
single-estimator volatility-regime gates already tested and rejected in
this repo. Best full-sample Sharpe (QQQ, 0.686) falls short of threshold;
crypto shows essentially zero edge. The underlying SMA(20/50) crossover
base rate is itself weak without the volatility gate contributing enough
lift to clear 1.0.
