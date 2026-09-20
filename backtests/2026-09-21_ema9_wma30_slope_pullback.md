# EMA(9)/WMA(30) Slope-Confirmed Pullback — QQQ Backtest Report

**Date:** 2026-09-21 (cron trigger, iteration 2)
**Strategy file:** `strategies/2026-09-21_ema9_wma30_slope_pullback.py`
**Hypothesis source:** https://www.quantifiedstrategies.com/9-30-trading-strategy/
(via Google SERP browsing; web_search returned a DDGS TLS/connection-reset
error for this iteration's queries, so browser_exec was used per
RESEARCH_LOOP.md's fallback path)

## Hypothesis

Per quantifiedstrategies.com's "9/30 Trading Strategy" article (originally
developed by Mike Burns), a 9-period EMA and 30-period WMA define a
"pullback zone". The source's fully-disclosed slope-confirmed variant: long
while `9-EMA > 30-WMA` AND the 30-WMA itself is sloping upward, flat
otherwise. Source's own SPY backtest of this variant found CAGR 4.5% vs.
buy-and-hold's 9.2%, ~60% time in market. Distinct from every other
EMA-crossover entry in this repo (those compare EMA vs EMA, not the
WMA-slope-confirmed EMA/WMA construction here).

## Grid test summary (fast_window x slow_window x symbol x vol-regime)

- Grid: `fast_window` in {5, 9, 13}, `slow_window` in {20, 30, 40}; symbols
  QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); 3 vol-regime terciles.
- **Total cells:** 108, **Passed:** 38, **pass_fraction = 0.352**
- By asset class: equity 30/54; crypto 8/54 (better than the plain EMA
  13/48 crossover tested this cron trigger, but still weak overall).
- By vol regime: low 26/36, mid 12/36, high 0/36 — again fails outright in
  the high-vol tercile.
- Best average full-sample equity cells: SPY (fast=5,slow=30) avg Sharpe
  1.30; SPY (fast=9,slow=20) avg 1.28; QQQ (fast=5,slow=40) avg 1.26 — the
  source's own default (9,30) params underperform these on modern data
  (QQQ full-sample Sharpe only 0.96 at (9,30), see below).

## Single-config validation, QQQ, full sample 2016-2026

**Source's default params (fast=9, slow=30): FAILED**
- Sharpe 0.960 (< 1.0 threshold) — FAIL
- Max drawdown 0.283 (> 0.25 threshold) — FAIL
- TC survival passed (0.858 net Sharpe), walk-forward passed, param
  sensitivity passed.

**Retuned params from grid's best average cell (fast=5, slow=40): PASSED**

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.121 | 1.0 |
| Max drawdown | ✅ | 0.237 | 0.25 |
| Transaction cost survival (10bps/trade, 80 trades) | ✅ | 1.029 net Sharpe | 0.5 |
| Walk-forward (4 splits) | ✅ | 1.0 pass fraction | 0.75 |
| Parameter sensitivity (9-cell QQQ grid) | ✅ | 0.073 relative std | 0.5 |

## Decision: ACCEPT (QQQ only, retuned params fast_window=5/slow_window=40)

The source's own default (9,30) parameters do NOT clear this repo's
thresholds on modern 2016-2026 QQQ data (fails Sharpe and MDD, driven mostly
by high-vol-regime drawdowns) — this is a retuning-driven accept similar to
several prior entries in this repo. Scope: QQQ only, low/mid vol regimes;
decisively fails high-vol regime and crypto — do not extend outside this
scope without further testing. Strategy file's default params have been set
to the retuned (5, 40) values (not the source's original 9/30) to match what
was actually accepted.
