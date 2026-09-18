# 2026-09-18-069: Monthly ETF Rotation (200d SMA Trend Filter + ROC Ranking, Top-N)

## Hypothesis

Per FabTrader's "ETF Rotation Strategy: A Four-Year Historical Backtest"
(https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr),
the source discloses a monthly rotation rule: (1) TREND FILTER -- ETF must
trade above its 200-day SMA to be eligible; (2) MOMENTUM RANK -- eligible
ETFs ranked by trailing ROC (source tests 1/2/3-month lookbacks); (3)
SELECT top-N ranked, equal-weighted; (4) monthly rebalance (month-open
entry, month-close exit).

Adapted to this repo's single-asset interface the same way the existing
5-asset momentum rotation gate handles cross-asset signals: internally
loads a US-tradable basket (QQQ, SPY, IWM, GLD, TLT, EFA, EEM -- broad
US/small-cap/gold/long-treasuries/developed-ex-US/emerging-markets proxies,
distinct universe from the source's Indian-market ETF list since
data/loaders.py only fetches US-listed tickers), computes the 200d-SMA
eligibility + ROC rank at each month-end, and returns position=1 for the
primary asset only during months when it is both eligible AND in the
top-N selected set.

Source: https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr

First strategy in this repo combining an explicit 200d-SMA ELIGIBILITY gate
with ROC-based cross-sectional RANKING in a single-asset basket-gate
adaptation.

## Parameter scan (QQQ/SPY primary, basket-internal rotation logic;
trend_window in [150,200] x roc_lookback_months in [1,3,6] x top_n in
[2,3,4], 18 combos x 2 symbols, vol_regime_splits=3, 2018-01-01..2026-09-01)

Best average-across-vol-regimes config: **QQQ, trend_window=200,
roc_lookback_months=1, top_n=3**, avg Sharpe 1.280, pass 2/3 vol regimes.
SPY's best config (roc_lookback_months=1, top_n=4, trend_window=200) only
reached avg Sharpe 1.002, pass 1/3.

## Single-config validation (trend_window=200, roc_lookback_months=1,
top_n=3, 2018-01-01..2026-09-01)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.939 (**fail**) | 0.501 (**fail**) | 1.0 |
| Max drawdown | 0.286 (**fail**) | 0.239 (pass) | 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.913 (pass, 27 trades) | 0.445 (**fail**, 35 trades) | 0.5 |
| Walk-forward (4 splits, manual substitute*) | 1.00 (4/4, pass) | 1.00 (4/4, pass) | 0.75 |
| Parameter sensitivity (relative std, 18-combo grid) | 0.249 (pass) | 0.735 (**fail**) | 0.5 |

\* `validation/validators.py::check_walk_forward` errors on the installed
vectorbt 1.1.0; substituted a manual 4-equal-split walk-forward with the
identical pass criterion (see prior iterations' established fallback).

Crypto asset-class breadth: not applicable by construction -- this
strategy's basket (QQQ/SPY/IWM/GLD/TLT/EFA/EEM) is a US cross-asset ETF
universe with no natural crypto member; consistent with how the existing
5-asset momentum rotation gate strategy also scopes itself to
equity/cross-asset-ETF baskets only.

## Decision

**Rejected.** QQQ is a genuine near-miss: Sharpe 0.939 (vs 1.0) and MDD
0.286 (vs 0.25) both miss narrowly, while transaction-cost survival,
walk-forward, and parameter sensitivity all pass cleanly. SPY fails more
decisively (Sharpe 0.501, TC-survival 0.445, parameter sensitivity 0.735).
A future iteration could try: (a) a shorter roc_lookback (already tested
1/3/6 months, 1-month was best -- could test 2 weeks / 10-15 trading days
finer granularity), (b) adding a max-drawdown-triggered de-risking overlay
to address QQQ's MDD miss specifically, or (c) expanding the basket to
include a defensive/cash-equivalent asset (e.g. SHY/BIL) so the rotation
can flee to cash during broad risk-off periods instead of always holding
top-N regardless of absolute momentum sign.
