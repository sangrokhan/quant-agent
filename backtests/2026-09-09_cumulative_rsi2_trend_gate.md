# Cumulative RSI(2), 200-day SMA Trend-Gated — QQQ/SPY/BTC/ETH

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_cumulative_rsi2_trend_gate.py`
**Outcome:** REJECTED (all symbols)

## Hypothesis

Per Larry Connors' "Short Term Trading Strategies That Work" (as disclosed
at https://www.elitetrader.com/et/threads/larry-connors-cumulative-rsi-26-annual-return-now-with-sensitivity-analysis.379982/):
sum RSI(2) over the trailing 2 days into a "cumulative RSI"; buy next open
when cumulative RSI < 10, exit next open when cumulative RSI > 65, only
trade above the 200-day SMA. Distinct new indicator construction from
Connors RSI (2026-09-04-113, average of 3 different oscillators) and plain
RSI(2) (2026-09-03-005, single-day snapshot) -- this is a SUM of RSI(2)
across days, not a composite average.

## Grid test (Step 6)

`param_grid`: entry_threshold in [5, 10, 15], exit_threshold in [55, 65, 75]
`symbols`: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
`vol_regime_splits`: 3
Total cells: 108, passed: 10, **pass_fraction: 0.093**

By asset class: equity 10/54, crypto 0/54 (decisive rejection).
By vol regime: low 10/36, mid 0/36, high 0/36 -- edge exists ONLY in
low-vol regime, nowhere else.

Best average-Sharpe param combo across cells (equity): entry=15/exit=65
(avg Sharpe 0.571 across vol-regime slices, 2/6 cells passing).
Best single cell: entry=15/exit=55, QQQ, low-vol, Sharpe 2.39.
Worst cell: entry=5/exit=75, QQQ, mid-vol, Sharpe -1.09.

## Single-config validation (Step 7), best-average config entry=15/exit=65

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.243 (FAIL) | 0.253 (FAIL) | >= 1.0 |
| Max drawdown | 0.078 (PASS) | 0.074 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.159 net Sharpe (FAIL) | 0.129 net Sharpe (FAIL) | >= 0.5 |
| Walk-forward (4 splits) | 0.75 (PASS, borderline) | 0.75 (PASS, borderline) | >= 0.75 |
| Parameter sensitivity | rel_std 0.726 (FAIL) | rel_std 1.969 (FAIL) | <= 0.5 |

## Decision

**REJECTED.** Full-sample Sharpe decisively fails on both QQQ and SPY
(0.24 / 0.25 vs 1.0 required), driven by very low trade frequency (26
trades over ~7.5yr) -- the double-day cumulative requirement makes the
signal rare, so full-sample results are dominated by long flat stretches
earning nothing while the underlying still appreciates (opportunity cost).
Parameter sensitivity also fails badly for both symbols (relative std
0.73/1.97), meaning results are not robust across neighboring threshold
choices -- exactly what Connors' own sensitivity-analysis caveat in the
source thread warns against over-relying on. Grid pass_fraction only
0.093/108, edge concentrated exclusively in the low-vol regime. Not a
promising near-miss worth refining; the mechanism (summed RSI(2) trigger)
appears too rare/noisy at single-symbol scale to clear this repo's
thresholds, though the source's own portfolio-level (multi-stock,
max-3-positions) construction reports much better numbers -- that's a
different implementation shape (multi-asset selection/ranking) outside
this iteration's single-symbol scope.

## Source

https://www.elitetrader.com/et/threads/larry-connors-cumulative-rsi-26-annual-return-now-with-sensitivity-analysis.379982/
