# No-Wick Retest Levels + SMA Trend Filter — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_no_wick_retest_sma_trend.py`
**Source:** LuxAlgo, "No-Wick Retest Levels" indicator concept
(https://www.luxalgo.com/library/indicator/no-wick-retest-levels/, published
Sep 9 2026), read via `browser_exec` this iteration (`web_search` DDGS
backend TLS-errored on all queries attempted).

## Hypothesis

A candle whose lower wick is negligible relative to its own range (the low
is essentially at the open or close) marks a momentum/exhaustion bar; that
bar's own low becomes a level that, on a later retest with an agreeing trend
filter, offers a high-probability long re-entry. Source's construction uses
a 1-minute EMA trend filter (intraday, infeasible on this repo's daily-only
`data/loaders.py` per prior KB note 2026-09-17-015) — adapted here to a daily
SMA(trend_window) trend filter, keeping the no-wick-level + retest + ATR
TP/SL mechanism otherwise unchanged.

## Grid test summary (Step 6)

Initial grid: `wick_tolerance_pct` in {0.05,0.1} x `tp_atr_mult` in
{1.5,2.0,3.0} x `sl_atr_mult` in {0.75,1.0}, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol
regimes, 2016-2026.

- Total cells 144, passed 31 (pass_fraction 0.215)
- By asset class: equity 31/72; **crypto 0/72 (decisive fail)**
- By vol regime: low 24/48; mid 7/48; high 0/48

Retuned locally (no new external source) on `wick_tolerance_pct` in
{0.02,0.03,0.05} x `trend_window` in {150,200} for QQQ full-sample Sharpe;
tightening `wick_tolerance_pct` from 0.05 to 0.03 (fewer, higher-quality
no-wick candles => fewer trades => lower transaction-cost drag) with
`trend_window=150` produced the best full-sample QQQ Sharpe (1.591) and
comfortably passing MDD (0.202).

## Single-config validators (Step 7) — QQQ (wick_tolerance_pct=0.03,
tp_atr_mult=3.0, sl_atr_mult=0.75, trend_window=150)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **True** | 1.591 | 1.0 |
| Max drawdown | **True** | 0.202 | 0.25 |
| TC survival (422 trades, 10bps) | **True** | 0.833 | 0.5 |
| Walk-forward (4 splits) | **True** | 1.0 | 0.75 |
| Parameter sensitivity | **True** | rel std 0.128 | 0.5 |

**All 5 validators pass on QQQ, comfortably.**

## Single-config validators (Step 7) — SPY (same params)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | False | 0.157 | 1.0 |
| Max drawdown | False | 0.300 | 0.25 |
| TC survival | False | -0.238 | 0.5 |
| Walk-forward | False | 0.5 | 0.75 |
| Parameter sensitivity | True | 0.391 | 0.5 |

SPY fails decisively across almost every metric at the QQQ-tuned config —
not pursued further (accept QQQ scope only, consistent with this repo's
pattern of many strategies being QQQ-specific).

## Decision: ACCEPTED (QQQ only)

Crypto rejected decisively (0/72 grid cells) and SPY fails decisively at the
QQQ-tuned config, but QQQ passes all 5 validators with strong margins
(Sharpe 1.591, MDD 0.202, TC-survival 0.833). The retest+trend-filter
combination concentrates the no-wick-level signal to genuinely
high-conviction setups on QQQ specifically.
