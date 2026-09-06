# Triple Witching Week Seasonal (Long Monday Open, Exit Thursday Close) — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_triple_witching_week_seasonal.py`
**Outcome: REJECTED**

## Hypothesis

Triple witching (quarterly simultaneous expiration of stock options, stock
index options, and stock index futures on the 3rd Friday of March/June/
September/December) creates a systematic pre-expiration drift from dealer
gamma-hedging/rebalancing flows. Per BigPic Solutions' backtested rule
(disclosed fully in a Google SERP snippet; source page itself 404'd): "Go
long Monday open of witching week, exit Thursday close. Average gain: +0.55%
per trade, 65% win rate across 128 backtested trades."

Distinct from the already-tested (and rejected) monthly OPEX-week strategy
(2026-09-06-149) — triple witching is the quarterly subset where index
futures ALSO expire simultaneously.

Source: google_search SERP snippet for "Triple Witching week stock market
effect strategy rules quarterly" (bigpicsolutions.com's own page 404'd but
the exact numeric rule was captured in the search snippet itself).

## Step 6 — Grid test

48 cells: `entry_weekday_offset` [0,1] × `exit_weekday_offset` [3,4], symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2015-2026.

- **pass_fraction: 0.0625 (3/48)**
- by_asset_class: equity 3/24 (12.5%), crypto 0/24 (0%)
- by_vol_regime: low 3/16 (19%), mid 0/16 (0%), high 0/16 (0%)
- best_cell: QQQ, entry=Monday/exit=Thursday, low-vol slice, Sharpe 1.266
- worst_cell: SPY, entry=Tuesday/exit=Thursday, high-vol slice, Sharpe -1.677

## Step 7 — Single-config validation (source's own exact rule: entry=Monday,
exit=Thursday)

| Symbol | Sharpe (full sample) | MDD | TC-adj Sharpe (10bps, N trades) |
|---|---|---|---|
| QQQ | 0.012 (FAIL, thr 1.0) | 0.143 (PASS, thr 0.25) | -0.071 (FAIL, thr 0.5; 46 trades) |
| SPY | -0.662 (FAIL, thr 1.0) | **0.300 (FAIL, thr 0.25)** | -0.734 (FAIL, thr 0.5; 46 trades) |

Walk-forward / parameter sensitivity: not run given the decisive full-sample
failure on both symbols (Sharpe near-zero/negative on both).

## Decision

**Rejected, decisively.** Full-sample Sharpe is essentially zero on QQQ
(0.012) and clearly negative on SPY (-0.662) — the source's own claimed
+0.55%/trade, 65% win-rate edge (over 128 backtested trades, presumably a
different/shorter sample period and possibly SPX/ES futures rather than
QQQ/SPY ETFs) does not replicate over this repo's full 2015-2026 QQQ/SPY
daily-bar sample. SPY additionally BREACHES the max-drawdown threshold
(0.300 vs 0.25) — the 46-trade sample (roughly one trade per quarter over
11.7yr) includes at least one badly-timed witching week (plausibly
overlapping a broader market selloff, e.g. 2020 COVID or 2022 rate-hike
quarters) that dominates the small-sample drawdown. Crypto is unsuitable
across the entire grid (0/24).

## Notes for future loops

Do not retry this exact rule (Monday-open/Thursday-close of triple-witching
week) on QQQ/SPY daily bars — decisively falsified, near-zero-to-negative
full-sample Sharpe on both symbols tested. If revisiting the underlying
triple-witching seasonal premise, a shorter intraday window immediately
around Friday's expiration itself (not the whole week) or a shorter,
more-recent backtest sample (to match whatever period the source's 128-trade
claim was drawn from) might be worth trying, but the broad weekly window
tested here shows no edge over the long sample this repo uses.
