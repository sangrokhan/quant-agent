# Gap-and-Go Continuation Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_gap_and_go_continuation.py`
**Source:** https://www.tradezella.com/blog/gap-and-go-strategy

## Hypothesis

Gaps caused by genuine catalysts (min 2% gap-up, per source, but not "too
large" i.e. <=10% to avoid early fade risk) attract continuation momentum.
Adapted to daily bars: enter at the close of a gap-up day that also closed
green (follow-through proxy), hold a short window, exit on failed follow-
through (close below the gap day's open) or a max_hold_days time-stop.

## Single-config validator results (min_gap_pct=0.02, max_hold_days=3, source defaults)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | -0.672 | 1.0 | FAIL | 0.259 | 0.25 | FAIL |
| SPY | -0.379 | 1.0 | FAIL | 0.196 | 0.25 | PASS |

Decisive negative Sharpe on both tickers at the source's own recommended
gap-size threshold -- gap-ups on QQQ/SPY (index ETFs, which gap far less
dramatically and less often on true single-stock catalysts than the
individual equities the source's guide targets) do not show continuation
momentum at this daily-bar granularity; if anything the signal is mildly
negative (a mean-reversion tendency after the gap, not continuation).

## Grid test summary

`param_grid={"min_gap_pct": [0.01, 0.02, 0.03], "max_hold_days": [2, 3, 5]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.046 (5/108 cells)**
- by_asset_class: equity 5/54 passed; crypto 0/54 passed (decisive reject for crypto)
- by_vol_regime: low 2/36, mid 3/36, high 0/36
- best_cell: min_gap_pct=0.01, max_hold_days=5, QQQ, low-vol, Sharpe 1.71
- worst_cell: min_gap_pct=0.02, max_hold_days=3, QQQ, high-vol, Sharpe -1.27

Only a looser threshold (1% gap, below the source's own recommended 2%
minimum) shows any promise, and only in the low-vol regime on one symbol --
a narrow, parameter-fragile finding, not a broad continuation edge.

## Decision: REJECTED

Decisive negative Sharpe on both QQQ and SPY at the source-recommended
default parameterization (2% gap threshold); grid pass_fraction (4.6%)
confirms the source's own guide (aimed at individual high-catalyst stocks,
intraday 30-90min holds) does not translate to a daily-bar, index-ETF
continuation edge. Crypto rejected outright (0/54). This is consistent with
academic literature on gap reversal already tested in this repo
(2026-09-03-010 gap-down-fade) -- index-level gaps on this timeframe appear
to mean-revert rather than continue.

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(decisive full-sample + grid failure already settles this).
