# Time Series Forecast (TSF) ADX-Gated Crossover — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_tsf_adx_crossover.py` | **Outcome: REJECTED**

## Hypothesis
Per arrowalgo.com's TSF explainer (browser_exec fallback — web_search
DuckDuckGo returned "No results found" for the first query), the Time
Series Forecast draws a linear-regression best-fit line through recent
closes, projected one bar forward. Source's explicit "Strategy 1: TSF
Crossover Entry" + own recommendation to pair with ADX(14)>25 to filter
false signals in choppy markets. Long entry: close crosses above TSF AND
ADX>threshold; exit: reverse cross, ADX drops below threshold, or time-stop.

Source: https://arrowalgo.com/time-series-forecast-tsf

## Grid test (tsf_window=[10,14,20] x adx_threshold=[20,25,30], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 108 cells total, 18 passed (pass_fraction 0.167)
- By asset class: equity 18/54, crypto 0/54 (decisive fail)
- By vol regime: low 16/36, mid 2/36, high 0/36
- Best cell: tsf_window=10/adx_threshold=25, SPY low-vol, Sharpe 2.44
- Best avg-across-regime configs: QQQ tsf_window=10/adx=30 avg Sharpe 1.06; SPY tsf_window=10/adx=20 avg Sharpe 1.01

## Single-config validators (per-symbol best avg configs)

| Validator | QQQ (tsf=10, adx=30) | SPY (tsf=10, adx=20) | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.629 **FAIL** | 0.496 **FAIL** | >= 1.0 |
| Max Drawdown | 0.249 PASS (barely) | 0.345 **FAIL** | <= 0.25 |
| TC survival (10bps) | 0.533 PASS | 0.289 **FAIL** | >= 0.5 |
| Walk-forward (4-split manual) | 0.75 PASS | 1.00 PASS | >= 0.75 |
| Parameter sensitivity | 0.782 **FAIL** | 2.676 **FAIL** (severe) | <= 0.5 |
| Trade count | 58 | 148 | n/a (SPY very high frequency at adx=20) |

Crypto context (tsf_window=10, adx_threshold=25, shared): BTC/USDT Sharpe
0.083, ETH/USDT Sharpe 0.100 — clear fail.

## Verdict
**REJECTED (decisive).** Both QQQ and SPY collapse at full-sample Sharpe
(0.63, 0.50) well below the grid's regime-average near-1.0 readings —
consistent regime-average-vs-full-sample overstatement pattern seen across
several recent iterations. SPY additionally fails MDD and TC-survival with
a very high 148-trade count at the looser adx_threshold=20 setting.
Parameter sensitivity fails badly on both (relative std 0.78 and 2.68 —
the latter driven by a near-zero mean Sharpe across the 3x3 grid flipping
sign at several cells). Crypto decisively rejected. The TSF+ADX combination
does not survive full-sample validation despite the source's own explicit
strategy recommendation.
