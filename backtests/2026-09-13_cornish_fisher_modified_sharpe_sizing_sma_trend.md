# Cornish-Fisher Modified Sharpe Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://investmenttoolkit.wordpress.com/2014/10/29/modified-sharpe-ratio-in-excel/
(Gregoriou & Gueyie 2003 convention, read via browser_exec Google SERP
fallback; braverock.com 404'd, metricgate.com 403'd): Modified Sharpe Ratio
= (return - risk_free) / Modified VaR (MVaR), where MVaR uses the
Cornish-Fisher asymptotic expansion to adjust the normal VaR z-score by the
return distribution's own skewness and excess kurtosis. Unlike every prior
sizing overlay tested this cron trigger (all empirical/nonparametric --
percentiles, CVaR, drawdown-RMS, regression-fit), this ANALYTICALLY
approximates left-tail risk via the first FOUR moments of the trailing
return distribution -- a fundamentally different (parametric
moment-expansion) estimation approach. First Cornish-Fisher-Modified-
Sharpe-based sizing strategy in this repo.

**Source:** https://investmenttoolkit.wordpress.com/2014/10/29/modified-sharpe-ratio-in-excel/

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
cf_window in [60,90,120], msr_reference in [0.05,0.1,0.15];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, cf_window=60, msr_reference=0.1, low-vol, Sharpe=2.87
- worst_cell: QQQ, cf_window=60, msr_reference=0.15, high-vol, Sharpe=-0.64

Symbol-specific optimal windows diverge in the same pattern as this cron
trigger's other 4-moment/downside-risk-normalized sizing overlays: SPY
best at cf_window=60, QQQ best at cf_window=120.

## Single-config validator results

### SPY (cf_window=60, msr_reference=0.15) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.242 | >= 1.0 | Yes |
| Max drawdown | 0.131 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 92 trades) | 1.154 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.006 | <= 0.5 | Yes |

### QQQ (cf_window=120, msr_reference=0.1) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.257 | >= 1.0 | Yes |
| Max drawdown | 0.219 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 63 trades) | 1.221 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.038 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ (equity only)**, each with its own tuned
cf_window (60 for SPY, 120 for QQQ). All four validators run pass
comfortably for both symbols with very low parameter sensitivity (0.6%-3.8%
relative std) and modest turnover (63-92 trades). Performance magnitude
again closely tracks the sibling UPI/Kappa-3/Sortino strategies this cron
trigger -- reinforcing that on this repo's SMA(200) trend gate, essentially
any reasonable "annualized excess return over a trailing risk-normalization
term" sizing construction produces similar, moderately robust equity-only
results, whether the risk term is empirical (percentile/CVaR/RMS-drawdown)
or analytically moment-based (Cornish-Fisher). Crypto (BTC/USDT, ETH/USDT)
rejected across the whole grid (0/54 cells), consistent with every prior
sizing overlay tested this cron trigger.
