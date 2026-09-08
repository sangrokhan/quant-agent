# Bump-and-Run Reversal (BARR) Bottom — Backtest Report

**Date:** 2026-09-08 (iteration 8, cron trigger 2026-09-09)
**Strategy file:** `strategies/2026-09-09_bump_and_run_reversal_bottom.py`
**Source:** https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/bump-and-run-reversal

## Hypothesis

The Bump-and-Run Reversal (Bulkowski's own testing ranks it among the
highest-performing of 39 chart patterns): a 3-phase pattern — (1) an
orderly lead-in trend (moderate-slope trend line), (2) a "bump" phase
where price accelerates away from the extrapolated trend-line projection
by a meaningful percentage (a speculative/panic move), (3) a "run" phase
that begins when price closes back across the extrapolated lead-in trend
line. Source's own exact entry rule: "wait for the price to break and
close completely... beyond the lead-in trend line" to trigger entry;
stop-loss placed "just beyond the extreme peak/trough of the bump phase".
First BARR pattern tested in this repo.

## Grid test summary (Step 6)

Grid: `lead_in_window in {30,40}`, `bump_threshold_pct in {0.05,0.08}`,
`reward_mult in {1.0,1.5}` x symbols `{QQQ,SPY,BTC/USDT,ETH/USDT}` x
vol_regime_splits=3. 2018-01-01 to 2026-09-01.

- `total_cells=96`, `passed_cells=27`, `pass_fraction=0.281`
- `by_asset_class`: equity 27/48 PASS; **crypto 0/48 (decisive reject)**
- `by_vol_regime`: low 8/32, mid 11/32, high 8/32 — unusually EVEN
  spread across all three vol regimes (unlike most trend-following
  strategies in this repo which concentrate almost entirely in low-vol);
  this pattern's panic-acceleration-then-reversal mechanic plausibly
  works across a range of volatility conditions since it's defined
  relative to its own recent trend, not an absolute vol level.
- `best_cell`: QQQ, lead_in_window=40/bump_threshold_pct=0.08/
  reward_mult=1.5, MID-vol, Sharpe 2.30.

## Single-config validator results (full sample, per-symbol tuned)

| Metric | QQQ (`lead_in_window=40,bump_threshold_pct=0.08,reward_mult=1.5`) | SPY (`lead_in_window=30,bump_threshold_pct=0.05,reward_mult=1.5`) |
|---|---|---|
| Sharpe ratio | 1.040 (PASS, narrow) | 1.111 (PASS) |
| Max drawdown | 0.075 (PASS) | 0.154 (PASS) |
| Net Sharpe after costs (10bps/trade) | 1.021 (PASS) | 1.090 (PASS) |
| Parameter sensitivity (relative std, 3x3 grid) | 0.165 (PASS) | 0.328 (PASS) |
| Walk-forward (manual 4-split substitute) | `[0.424, 1.078, 1.334, -0.561]` (3/4 positive = 0.75, PASS at threshold) | `[1.485, 0.559, 1.163, 2.132]` (4/4 positive, PASS) |

**Caveat (same pattern as 2026-09-09-043):** low trade counts — QQQ 8
trades, SPY 10 trades over the full ~8.7yr sample. This is a genuinely
rare, high-conviction pattern per its own 3-phase definition, but the
statistical confidence in the Sharpe/MDD figures is correspondingly
weaker than for higher-frequency strategies. QQQ's Sharpe (1.040) is also
a narrow pass, not a comfortable margin above 1.0.

## Decision

**ACCEPTED for equity (QQQ, SPY)** — per-symbol tuned configs, both with
low trade counts flagged honestly as a confidence caveat.
**REJECTED for crypto** (BTC/USDT, ETH/USDT) — decisive 0/48 grid cells.

Scope note: unlike most strategies in this repo, this pattern's edge is
NOT concentrated in low-vol regimes — it appears across low/mid/high vol
roughly evenly, which is a notable and unusual finding worth flagging for
future loops looking at genuinely all-weather equity signals.
