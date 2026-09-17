# Backtest Report: Volatility Switch (VOLSWITCH) Percentile-Rank Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-17_volswitch_pctrank_sizing_sma_trend.py`
**Date:** 2026-09-17 (cron trigger iteration 2/10)

## Hypothesis

Volatility Switch (VOLSWITCH, Ron McEwan, TASC Feb 2013) per TASC's own
EasyLanguage Traders' Tips code (source:
https://traders.com/Documentation/FEEDbk_docs/2013/02/TradersTips.html,
read via browser_exec this iteration -- web_search's DDGS backend
intermittently errored/returned no results for several queries this
iteration, Google search fallback used for keyword discovery):
`VolSwitch = Count / Length` where Count counts how many of the trailing
`Length` rolling-std-dev-of-symmetric-pct-change readings are <= TODAY's
reading -- i.e. a percentile-rank-of-current-volatility construction. This
repo's prior VOLSWITCH entry (2026-09-16-095) used a min-max normalization
approximation instead and was rejected on SPY with no rescue found; this
sub-iteration swaps in TASC's exact percentile-rank formula to test
whether the more faithful construction fixes that rejection, reframed as
an inverse continuous sizing dial (low VolSwitch -> more exposure) within
an SMA(trend_window) uptrend gate, same pattern as the prior entry.

## Grid test summary (Step 6)

108 cells: param_grid={trend_window:[30,40,50], sensitivity:[0.5,0.6,0.7]}
(vol_length=21, deadband=0.20 fixed) x symbols {equity: QQQ,SPY; crypto:
BTC/USDT,ETH/USDT} x vol_regime_splits=3.

- pass_fraction: 0.343 (37/108)
- by_asset_class: equity 19/54, crypto 18/54
- by_vol_regime: low 32/36, mid 5/36, high 0/36 (works only in calm
  regimes, fails almost entirely once volatility rises -- expected for an
  inverse-volatility-conditioning sizing dial)
- best_cell: SPY low-vol, trend_window=30 sensitivity=0.5, Sharpe 2.19

## Single-config validation (Step 7) -- parameter sweep, no config clears both symbols

Swept deadband in {0.15, 0.30, 0.45}, trend_window in {20, 30},
vol_length in {14, 21, 30}, sensitivity in {0.5, 0.6, 0.7}, base_exposure
in {0.4, 0.5, 0.6}, and leverage_cap up to 1.2 -- 30+ configs tried.
QQQ's full-sample Sharpe occasionally cleared 1.0 (best ~1.045 at
trend_window=20, vol_length=21, deadband=0.15), but **SPY's full-sample
Sharpe never exceeded ~0.73 across any config tried** (typical range
0.55-0.73), always well below the 1.0 threshold. No config found that
clears the Sharpe validator on both required equity symbols.

## Decision

**Reject.** The TASC-exact percentile-rank construction did not rescue
the prior SPY near-miss from 2026-09-16-095 -- SPY's Sharpe stayed
persistently sub-1.0 (0.55-0.73 range) across a broad parameter sweep,
a decisive (not near-miss) failure. No further validators run since
Sharpe alone already rules this config out on SPY.
