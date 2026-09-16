# 2026-09-17: RSI(2) Trend-Resumption Entry + Fast RSI-Recovery Exit — REJECTED

## Hypothesis

Direct follow-up to this same cron trigger's 2026-09-17-002 (RSI(2)
trend-resumption confirmation entry + N-day low-of-lows trailing exit,
rejected as a near-miss: full-sample Sharpe 0.871 QQQ / 0.643 SPY vs 1.0
threshold). That report's notes suggested the slow low-of-lows exit was
likely the main driver of the shortfall, not the entry timing, and
recommended testing the same confirmation-gated entry against a faster
RSI-recovery exit instead — per the source article's own "Trend Resumption
— RSI Exit" comparison row
(https://alvarezquanttrading.com/blog/mean-reversion-entry-timing/, same
source read this trigger).

## Strategy file

`strategies/2026-09-17_rsi2_trend_resumption_fastexit.py`

## Step 6 — Grid test

Grid: `rsi_entry` in [10, 15, 20], `rsi_exit` in [50, 60, 70]; symbols
equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]; vol_regime_splits=3.
108 total cells (2019-01-01 to 2026-09-01).

- pass_fraction: **25/108 = 0.231** (broader-regime spread than the
  low-of-lows variant: low 14/36, mid 6/36, high 5/36 — vs. the prior
  strategy's 18/3/0)
- by_asset_class: equity 23/54, crypto 2/54
- best_cell: rsi_entry=15, rsi_exit=50, SPY, low-vol, Sharpe=2.43
- worst_cell: rsi_entry=10, rsi_exit=70, BTC/USDT, low-vol, Sharpe=-1.50

## Step 7 — Standard validators (primary config: grid best_cell params)

`rsi_entry=15.0, rsi_exit=50.0, trend_window=200, max_hold_days=15, rsi_window=2`

| Symbol | Sharpe | MDD | TC net Sharpe | Trades |
|---|---|---|---|---|
| QQQ | 0.445 (fail, thr 1.0) | 0.076 (pass) | 0.238 (fail, thr 0.5) | 78 |
| SPY | 0.912 (fail, thr 1.0) | 0.064 (pass) | 0.501 (pass, thr 0.5) | 80 |

Parameter sensitivity (rsi_entry sweep, QQQ): rel_std 0.155 (pass, thr 0.5).
Walk-forward validator errored (`vectorbt.utils.splitting` unavailable in
this environment) — not usable this iteration.

## Decision (Step 8)

**Rejected.** Both QQQ and SPY full-sample Sharpe fail the 1.0 threshold,
and this fast-exit variant is actually WORSE on full-sample Sharpe than the
slow low-of-lows-exit sibling (2026-09-17-002: 0.871/0.643 vs this: 0.445/
0.912) despite a much broader grid pass-fraction and vol-regime spread
(0.231 vs 0.194, more balanced low/mid/high). The very low MDD (0.06-0.08)
and higher trade count (78-80 vs 32-34) suggest the fast RSI(50) exit
recycles capital quickly into many small, low-conviction trades rather than
capturing fewer larger moves — net effect is lower risk-adjusted return
despite the broader grid coverage. Hypothesis disproven: contrary to the
prior report's own prediction, the exit choice was NOT simply "swap for
faster = fixes it" — both exit variants of this same trend-resumption entry
fail the primary Sharpe bar, just via different mechanisms (regime-narrow
outperformance vs. broad-but-diluted-by-overtrading).

## Notes for future loops

- Both siblings of the trend-resumption confirmation-entry family
  (2026-09-17-002 low-of-lows exit, this fast-RSI-exit variant) are now
  rejected near-misses. The confirmation-wait entry mechanic itself does
  not appear to be the missing ingredient for this repo's RSI(2)+SMA200
  setup family — the existing accepted plain-immediate-entry RSI(2)
  strategy (2026-09-03-005, 5-day-SMA-recovery exit) remains the
  repo's only accepted config in this specific indicator family. Do not
  retest RSI(2)+trend-resumption-entry again without a genuinely different
  exit/filter combination.
- QQQ's transaction-cost-survival fail (0.238 vs 0.5 threshold, on 78
  trades over ~7.7yr) flags that trade frequency is already testing the
  10bps/trade assumption's limits at this hold-period; any future
  fast-exit RSI(2) variant on QQQ should watch trade count closely.
