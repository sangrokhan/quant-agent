# Turn-of-the-Month, Trend-Filtered Follow-up — Backtest Report

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_turn_of_month_trend_filtered.py`
**Source:** Same as 2026-09-11-124 (Google AI-overview synthesis of ScienceDirect/QuantPedia/Forbes TOM literature)

## Hypothesis

Direct fix attempt for 2026-09-11-124 (plain TOM seasonality, rejected:
Sharpe 0.73/0.78 near-miss vs 1.0). That entry's notes suggested a trend
filter to concentrate entries in the favorable low-vol regime. This
iteration adds close > SMA(trend_window) to the same calendar-window logic.

## Grid test summary (Step 6)

`scripts/run_grid_tom_trend.py` — param grid `entry_days_before_month_end∈{4,6,8}`,
`exit_days_into_month∈{1,2,3}`, `trend_window∈{50,100,200}` × symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}` × 3 vol-regime terciles (324 total cells).

- **pass_fraction: 0.173** (56/324) -- LOWER than the un-gated version's 0.241
- **by_asset_class:** equity 56/162, crypto 0/162
- **by_vol_regime:** low 54/108, mid 2/108, high 0/108
- **best_cell:** QQQ, entry=8/exit=2/trend_window=200, low-vol, Sharpe 2.33

## Single-config validators (Step 7) — best grid config (entry=8, exit=2, trend_window=200), full sample 2010-2026

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | # trades |
|---|---|---|---|---|---|---|
| QQQ | **0.668 (FAIL, thr 1.0)** | 0.172 (pass) | 0.512 (pass) | 1.0 (pass) | 0.213 (pass) | 184 |
| SPY | **0.454 (FAIL, thr 1.0)** | 0.249 (pass, barely) | **0.262 (FAIL, thr 0.5)** | 0.75 (pass) | 0.144 (pass) | 185 |

**Counterintuitive result: the trend filter made full-sample Sharpe WORSE**,
not better (QQQ 0.733→0.668, SPY 0.783→0.454) despite improving the
best-cell grid Sharpe (1.81→2.33) and slightly improving MDD. This is
because filtering out mid/high-vol-regime months also filters out many of
the ordinary low-vol months that still contributed positive TOM returns --
the trend filter is a noisy proxy for "regime favorable to TOM" and removes
too many good months along with the bad ones on the full, unsliced sample.

## Decision: REJECTED

Both QQQ and SPY still fail Sharpe threshold, and SPY additionally fails
TC-survival. The proposed fix (trend filter) did not work as hypothesized
on the full sample -- confirms that vol-regime tercile-conditional grid
cells can overstate what a corresponding "regime gate" indicator achieves
once applied unconditionally across the whole history. Crypto decisively
rejected (0/162).

Notes for future loops: don't assume a grid's vol-regime-tercile pass
pattern directly implies a matching trend/vol-regime *filter* will improve
full-sample results -- the tercile split is retrospective and cherry-picks
already-favorable sub-periods, while a live filter has to decide in real
time and inevitably excludes some favorable periods too.
