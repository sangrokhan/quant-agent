# Backtest Report: Awesome Oscillator Bullish Saucer (SPY accepted; QQQ rejected)

**Strategy file:** `strategies/2026-09-04_ao_saucer_bullish.py`
**Date:** 2026-09-04

## Hypothesis

Bill Williams' Awesome Oscillator (AO = SMA(5, median_price) - SMA(34,
median_price)) "Bullish Saucer" setup — AO above the zero line, two
consecutive declining ("red") bars followed by a rising ("green") bar —
signals a sharper, more localized re-acceleration of already-positive
momentum than the plain zero-line cross tested previously
(id=2026-09-04-041, rejected as a near-miss on QQQ: Sharpe 0.89 vs 1.0
threshold). Gated by a close > SMA(200) uptrend filter. Exit on AO
crossing back below zero, a mirror-image Bearish Saucer firing, or
max_hold_days.

**Source:** https://www.tradingview.com/support/solutions/43000501826-awesome-oscillator-ao/
(official TradingView AO documentation — precise bar-by-bar rule
definitions for Zero Line Cross / Twin Peaks / Saucer setups).

## Grid test summary (Step 6)

param_grid = {trend_window: [100, 200], max_hold_days: [10, 15, 20]},
symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]},
vol_regime_splits=3, period 2019-01-01..2026-09-01.

- total_cells: 72, passed_cells: 16, **pass_fraction: 0.222**
- by_asset_class: equity 16/36 passed; **crypto 0/36 passed**
- by_vol_regime: low 12/24; mid 4/24; high 0/24 (decisively worse in
  high-vol regimes, consistent with a momentum-continuation strategy)
- best_cell: SPY, trend_window=200, max_hold_days=10, low-vol, Sharpe 2.79
- worst_cell: QQQ, trend_window=100, max_hold_days=15, high-vol, Sharpe -0.78

## Single-config validators (Step 7) — primary config: trend_window=200, max_hold_days=10

| Validator | SPY | QQQ |
|---|---|---|
| sharpe_ratio (>=1.0) | **PASS** 1.259 | **PASS** 1.236 |
| max_drawdown (<=25%) | **PASS** 6.85% | **PASS** 13.14% |
| transaction_cost_survival (10bps/trade, net Sharpe >=0.5) | **PASS** net 1.083 (47 trades) | **PASS** net 1.100 (45 trades) |
| walk_forward (4 manual date-slices; vectorbt splitter API unavailable in installed v1.1.0, same known workaround as prior iterations) | **PASS** 4/4 splits positive (1.0) | **FAIL** 2/4 splits positive (0.5 vs 0.75 threshold) |
| parameter_sensitivity (6-cell full-sample grid, relative std of Sharpe) | **PASS** 0.270 (mean 0.901) | **PASS** 0.330 (mean 0.788) |

## Decision

**ACCEPTED for SPY** (all 5 validators pass, full-sample Sharpe 1.26,
MDD only 6.85%, survives 10bps/trade costs, walk-forward robust 4/4).

**REJECTED for QQQ** — despite passing full-sample Sharpe/MDD/costs/param-
sensitivity, walk-forward fails (only 2/4 quarters of the sample positive),
indicating the QQQ edge is concentrated in specific sub-periods rather than
persistent — do not trust this strategy on QQQ.

**REJECTED for crypto (BTC/USDT, ETH/USDT)** — 0/36 grid cells passed;
the saucer setup's momentum-continuation logic does not transfer to 24/7
crypto markets in this sample, consistent with several prior AO/MACD-family
rejections in this repo (2026-09-04-041 AO zero-line, 2026-09-04-100 MACD
histogram inflection).

Distinct from the prior AO zero-line-cross test (2026-09-04-041): the
Saucer's requirement that AO is *already positive* before the signal fires
(vs. reacting to the cross itself) appears to filter out the noisier/
false-start entries that dragged the zero-line-cross variant's Sharpe down
to a near-miss 0.89 on QQQ — SPY here clears the bar decisively (1.26).
