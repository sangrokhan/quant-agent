# VQI Streak Confirmation + Realized-Vol Regime Gate — Backtest Report

**Date:** 2026-09-07 | **Strategy file:** `strategies/2026-09-08_vqi_streak_volregime_gate.py`

## Hypothesis

Direct follow-up to the near-miss VQI streak-confirmation strategy
already in this repo (id=2026-09-08-028): QQQ reached a near-miss
full-sample Sharpe of 0.941 (MDD/TC/WF/param-sens all passed), SPY and
crypto failed decisively. This repo's previously-productive fix pattern
(KAMA/ATR-band 2026-09-06-183, Elder-Ray Bull Power 2026-09-06-176) adds
an explicit realized-volatility regime gate (20d realized vol <= trailing
1yr median, identical construction to the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py`) restricting entries to the
low-vol regime, keeping VQI streak entry/exit logic otherwise unchanged.

## Step 6 — Grid summary (9 param combos x 4 symbols x 3 vol regimes = 108 cells)

- **Overall pass_fraction: 5/108 (4.6%) — WORSE than the ungated base strategy (18/48 = 37.5%)**
- By asset class: equity 5/54, crypto 0/54
- By vol regime: low 2/36, mid 2/36, high 1/36
- Best cell: SPY low-vol, streak_bars=8/max_hold=15, Sharpe 1.48
- Worst cell: QQQ low-vol, streak_bars=12/max_hold=15, Sharpe -1.20
- At the base config (streak_bars=10, max_hold=15): all 12 symbol/regime
  cells show Sharpe well below 1.0 (best 0.935 SPY high-vol, several
  negative)

## Step 8 — Decision: **REJECTED**

The realized-vol regime gate did NOT rescue the near-miss — it made
performance worse. Unlike the KAMA/ATR-band and Elder-Ray precedents
where the base strategy's edge was already visibly concentrated in one
vol tercile (making a gate a targeted fix), the base VQI strategy's edge
was fairly evenly distributed, so restricting entries to a
realized-vol-defined "low-vol" window (a different, coarser vol
partition than the grid tester's own within-window terciles) mostly just
reduced trade counts without concentrating the edge, hurting Sharpe
across nearly every cell. No single-config validator suite run given the
decisive grid degradation versus the un-gated predecessor.
