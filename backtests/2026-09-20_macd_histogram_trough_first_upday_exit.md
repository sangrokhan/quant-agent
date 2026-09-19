# MACD-Histogram Trough Entry / First-Up-Day Exit — Backtest Report (REJECTED)

## Hypothesis
Per QuantifiedStrategies.com's "MACD Histogram Trading Strategy"
(https://www.quantifiedstrategies.com/macd-histogram/, read via browser_exec
fallback after web_search's DDGS backend returned no results for the initial
queries this iteration): a standard MACD(12,26,9) histogram below zero that
just turned from falling to rising (a "trough" while still bearish) marks a
short-term bullish mean-reversion entry, exiting on the first day the close
is higher than the prior day's close (not a fixed hold or signal-based
exit). Source reports long-only much better than short-only on a 77-ETF
sample and a QLD (2x Nasdaq100) backtest since 2007 (85 trades, avg
gain 2.2%/trade, MDD 19%, invested only ~5% of the time).

## Step 6 — Grid test (fast x slow x signal, 2 asset classes, 3 vol regimes)

- `param_grid`: fast in {8,12,16}, slow in {21,26,30}, signal={9}
- `symbols`: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- `vol_regime_splits`: 3 (low/mid/high realized-vol terciles)
- Period: 2019-01-01 to 2026-09-19, daily bars

**Summary**: 108 cells total, 4 passed (pass_fraction = 0.037).
- by_asset_class: equity 3/54, crypto 1/54 — decisively narrow, does not
  hold up broadly.
- by_vol_regime: low 3/36, mid 0/36, high 1/36 — edge (what little exists)
  concentrated almost entirely in low-vol regimes.
- best_cell: QQQ, low-vol, fast=8/slow=21/signal=9, Sharpe 1.61 (isolated
  best-case slice, not representative of full-period performance).
- worst_cell: QQQ, mid-vol, fast=12/slow=30/signal=9, Sharpe -0.75.

## Step 7 — Single-config validators (best grid config: fast=8, slow=21,
signal=9, QQQ, full period 2019-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.273 | >= 1.0 | **FAIL** |
| Max drawdown | 0.281 | <= 0.25 | **FAIL** |
| Transaction cost survival (net Sharpe, 10bps/trade, 228 trades) | -0.015 | >= 0.5 | **FAIL** |
| Walk-forward (4 splits, manual RangeSplitter workaround — vectorbt's `vbt.utils.splitting` API is broken in the installed version) | 0.75 (3/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (fast/slow sweep: 8/21, 12/26, 16/30) | relative_std 0.431 | <= 0.5 | PASS |

## Decision: REJECTED

3 of 5 validators fail on the grid's own best-performing config (Sharpe,
max drawdown, transaction-cost survival). The grid-test pass_fraction of
3.7% confirms this isn't a narrow-scope-but-honest edge case (like some
prior accepted equity-only/low-vol-only strategies in this repo) — it fails
broadly across nearly every parameter/symbol/regime cell, including the
overall full-period run of its own best cell. 228 trades over ~7.7 years on
QQQ (roughly 30/year) makes the strategy highly transaction-cost sensitive,
and the source's own disclosed backtest (85 trades on leveraged QLD,
invested only 5% of the time) appears to have been substantially more
selective than what this literal MACD(12,26,9)-trough-turn / first-up-day
reconstruction produces on QQQ/SPY here — the source's precise numeric
threshold/filter for what counts as a qualifying "trough" is paywalled
("members only"), so this reconstruction is likely over-triggering relative
to their actual rule.

## Notes for future loops
A future iteration could try adding a minimum-histogram-depth filter (e.g.
require the histogram's local minimum to be below some z-score threshold,
not just any local uptick) to be more selective and closer to the source's
apparent 85-trades-over-18-years frequency, rather than the ~30/year rate
this literal reconstruction produces.
