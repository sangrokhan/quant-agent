# 2026-09-15 Trend Persistence Range (Poster) Filter on SMA Crossover

**Hypothesis:** Per Financial Hacker
(https://financial-hacker.com/petra-on-programming-the-trend-persistence-indicator/),
Richard Poster's Trend Persistence Range (S&C Feb 2021) measures, over a
rolling window, how consistently an SMA's slope points in one direction:
TPR = 100*|count_up-count_down|/period. Source's own honest finding: an
in-sample-optimized SMA-crossover-with-TPR-filter backtest nearly doubled
returns, but a walk-forward-optimized retest showed much smaller gains.
First TPR entry in this repo. Tested here as a trend-strength gate on an
SMA(fast)/SMA(slow) crossover.

**Best joint config:** fast_sma_period=10, slow_sma_period=40,
tpr_threshold=20

## Single-config validator results (full 2018-2026 sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward |
|---|---|---|---|---|
| QQQ | 0.967 (**FAIL** near-miss, thr 1.0) | 0.209 (pass) | 0.931 (pass) | 1.0 (pass) |
| SPY | 0.864 (**FAIL** near-miss, thr 1.0) | 0.168 (pass) | 0.813 (pass) | 1.0 (pass) |
| BTC/USDT | 1.078 (pass) | 0.462 (**FAIL** decisive, thr 0.25) | 1.061 (pass) | 1.0 (pass) |
| ETH/USDT | 0.986 (**FAIL** near-miss) | 0.541 (**FAIL** decisive) | 0.972 (pass) | 1.0 (pass) |

No symbol clears all validators: QQQ/SPY both Sharpe near-misses (walk-
forward and TC-survival and parameter-sensitivity all pass cleanly);
crypto decisively fails max-drawdown despite Sharpe passing on BTC.

## Grid summary (fast_sma_period in [10,20,30] x slow_sma_period in
[40,50,70] x tpr_threshold in [20,30,40], QQQ/SPY/BTC-USDT/ETH-USDT x
low/mid/high vol tercile, 324 cells)

- pass_fraction: 0.265 (86/324)
- by_asset_class: equity 79/162; crypto 7/162
- by_vol_regime: low 61/108; mid 25/108; high 0/108 (decisive high-vol
  failure across every combo/asset -- the plain SMA crossover underneath
  the TPR filter has no drawdown control mechanism of its own, so the
  filter alone cannot rescue high-vol-regime whipsaw/crash exposure)

## Outcome: REJECTED (all 4 symbols -- QQQ/SPY Sharpe near-misses, crypto
decisive MDD fail)

Confirms the source's own honest caveat: even with this repo's proper
walk-forward validator (not just in-sample optimization), the TPR filter
alone does not push a plain SMA crossover system over the Sharpe/MDD bar
on either equity or crypto. The near-misses on QQQ/SPY (both walk-forward
and parameter-sensitivity clean) suggest this could be a rescue candidate
for a future iteration (e.g. adding an explicit MDD control mechanism like
a vol-target overlay or a hard stop, since TPR itself is a trend-strength
filter, not a risk-control mechanism) -- but not pursued as a same-trigger
rescue given this cron trigger has already used two rescue sub-iterations.
