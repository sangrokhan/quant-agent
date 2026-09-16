# 2026-09-17: RSI(2) Trend-Resumption Entry + N-Day Low-of-Lows Exit — REJECTED

## Hypothesis

Per Cesar Alvarez's "Mean Reversion Entry Timing"
(https://alvarezquanttrading.com/blog/mean-reversion-entry-timing/, visited
this iteration via browser_exec — web_search's DDGS backend TLS-errored on
the initial query, resolved via a Google SERP fallback that surfaced the
article): compares mean-reversion entry-timing variants for an
RSI-oversold+uptrend setup. The article's "trend resumption" entry (wait for
price to clear the setup bar's own high before entering, rather than
entering immediately on the oversold reading) produced the highest average
CAR of the three entry variants tested (open-entry, intraday-pullback-limit,
trend-resumption) in the source's own 2007-2017 S&P500 test. The article
separately reports that swapping the usual fast RSI-recovery exit for an
"N-day low of lows" trailing-stop exit changes the risk/return profile
(lower win rate, higher CAR, larger MDD) — a slower, more trend-following-
style exit bolted onto a mean-reversion entry.

This repo's existing RSI(2) strategy (2026-09-03-005) enters immediately on
the oversold RSI reading with a fast 5-day SMA-recovery exit. This strategy
tests the structurally distinct combination: confirmation-gated entry (must
wait for high > setup bar's high) + N-day low-of-lows trailing exit +
max_hold_days safety backstop.

## Strategy file

`strategies/2026-09-17_rsi2_trend_resumption_lowoflows_exit.py`

## Step 6 — Grid test

Grid: `rsi_entry` in [10, 15, 20], `exit_lowoflows_window` in [5, 10, 20];
symbols equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]; vol_regime_splits=3.
108 total cells (2019-01-01 to 2026-09-01).

- pass_fraction: **21/108 = 0.194**
- by_asset_class: equity 21/54, crypto 0/54 (crypto decisively fails)
- by_vol_regime: low 18/36, mid 3/36, high 0/36 (heavily low-vol-concentrated)
- best_cell: rsi_entry=15, exit_lowoflows_window=5, SPY, low-vol, Sharpe=2.80
- worst_cell: rsi_entry=10, exit_lowoflows_window=5, QQQ, high-vol, Sharpe=-0.557

Pattern matches this repo's well-established finding: this construction only
passes in low-vol regimes and fails to generalize across regimes/asset
classes.

## Step 7 — Standard validators (primary config: grid best_cell params)

`rsi_entry=15.0, exit_lowoflows_window=5, trend_window=200, max_hold_days=30, rsi_window=2`

| Symbol | Sharpe | MDD | TC net Sharpe | Param sensitivity (rsi_entry sweep, QQQ) |
|---|---|---|---|---|
| QQQ | 0.871 (fail, thr 1.0) | 0.196 (pass, thr 0.25) | 0.836 (pass, thr 0.5) | rel_std 0.348 (pass, thr 0.5) |
| SPY | 0.643 (fail, thr 1.0) | 0.189 (pass, thr 0.25) | 0.598 (pass, thr 0.5) | — |

Walk-forward validator errored (`vectorbt.utils` has no attribute
`splitting` in this environment's installed vectorbt version — a known,
previously-documented repo/environment limitation, e.g. noted in the
2026-09-17 KDJ report) so was not usable as a pass/fail signal this
iteration; not counted toward the decision either way.

## Decision (Step 8)

**Rejected.** Full-sample Sharpe fails on both QQQ (0.871) and SPY (0.643)
against the 1.0 threshold, despite passing MDD, transaction-cost-survival,
and parameter-sensitivity. The grid's low-vol-concentrated pass pattern
(18/36 low, 3/36 mid, 0/36 high) confirms this is a narrow-regime effect
rather than a generalizable edge — consistent with the grid's own best_cell
being a low-vol single-symbol artifact. Crypto rejected decisively (0/54).

## Notes for future loops

- The confirmation-wait entry mechanic (only enter once high clears the
  setup bar's high) is itself a novel, reusable technique in this repo —
  distinct from every other RSI(2)/mean-reversion entry already tried
  (immediate-entry, N-day-persistence, cumulative-RSI, failed-bounce, etc.)
  — worth combining with a faster/different exit (e.g. the already-accepted
  5-day-SMA-recovery exit from 2026-09-03-005) in a future iteration rather
  than the slower N-day low-of-lows exit tested here, since the exit choice
  (not the entry timing) looks like the main driver of the full-sample
  Sharpe shortfall (near-miss magnitude ~0.13-0.36 below threshold on both
  symbols — a promising near-miss worth a follow-up).
- Source's "Entry on Open, N-Day Exit" and "Trend Resumption, N-Day Exit"
  comparison rows (not fully reproduced here) reported the N-day-exit
  variants having *higher* CAR but *lower* win rate than RSI-exit variants
  on the source's own Russell/S&P universe — the single-symbol daily-bar
  QQQ/SPY setting here may just have fewer qualifying setups for the effect
  to show through cleanly.
