# Parkinson-Vol-Targeting + Deadband (Crypto Rescue) — Backtest Report

**Date:** 2026-09-17 (cron trigger iteration 2)
**Strategy file:** `strategies/2026-09-17_parkinson_vol_targeting_deadband_crypto_rescue.py`
**Hypothesis:** Direct follow-up to this same cron trigger's iteration 1
(id 2026-09-17-050): the plain Parkinson-vol inverse-vol-targeting overlay
passed a higher fraction of crypto grid cells than equity ones on a raw
Sharpe/MDD basis (57% vs 47%), but was rejected for crypto because the
single-config validator run failed transaction-cost survival — daily
re-sizing with no deadband produced ~1400-1500 trades, wiping out the edge
after a 5bps/trade cost assumption. This iteration adds a rebalance-buffer
deadband (unchanged Parkinson-vol/SMA-trend construction otherwise), the
same turnover-control pattern already used in this repo (Donchian-ensemble
vol-targeting 2026-09-14-115, Amihud/Corwin-Schultz continuous-sizing dials
2026-09-16-139/140). No new external source this sub-iteration.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `trend_window`∈{100,200} × `vol_window`∈{10,20,40} × `target_vol`∈{0.10,0.15,0.20}
× `leverage_cap`∈{1.0,1.5} × `deadband`∈{0.10,0.20}, symbols={QQQ,SPY,BTC/USDT,ETH/USDT},
vol_regime_splits=3.

- total_cells: 864, passed: 445, **pass_fraction: 0.515**
- by_asset_class: equity 201/432 (0.47), crypto 244/432 (0.57)
- by_vol_regime: low 216/288 (0.75), mid 191/288 (0.66), high 38/288 (0.132)
- best_cell: SPY, trend_window=200/vol_window=10/target_vol=0.15/leverage_cap=1.5/deadband=0.2,
  low-vol regime, Sharpe 2.896
- worst_cell: QQQ, trend_window=100/vol_window=40/target_vol=0.10/leverage_cap=1.0/deadband=0.1,
  high-vol regime, Sharpe -0.554

Nearly identical breadth to the undeadbanded predecessor (0.515 vs 0.521
overall pass fraction) — the deadband doesn't change the underlying
signal's raw Sharpe/MDD profile much, confirming the predecessor's
diagnosis that the crypto rejection was a turnover/cost artifact, not a
raw-signal quality problem.

## Single-config validation (best per-symbol config found via 3-config search)

| Symbol | Config (trend_window/vol_window/target_vol/leverage_cap/deadband) | Sharpe | MDD | Net Sharpe (5bps) | # trades | WF pass frac | Param sens (rel std) |
|---|---|---|---|---|---|---|---|
| QQQ | 200/20/0.20/1.0/0.20 | 1.337 (pass) | 0.185 (pass) | 1.258 (pass) | 129 | 0.75 (pass) | 0.014 (pass) |
| SPY | 200/10/0.15/1.5/0.20 | 1.111 (pass) | 0.229 (pass) | 1.036 (pass) | 111 | 0.75 (pass) | 0.025 (pass) |
| BTC/USDT | 200/20/0.15/1.0/0.20 | **1.012 (pass)** | **0.176 (pass)** | **0.976 (pass)** | 69 | 0.75 (pass) | 0.095 (pass) |
| ETH/USDT | 200/20/0.20/1.0/0.20 | 0.946 (near-miss fail) | 0.244 (pass) | 0.924 (pass) | 60 | 1.00 (pass) | 0.042 (pass) |

The deadband collapses crypto turnover from ~1400-1500 down to 60-69 trades
(a ~20x reduction) — enough to clear the transaction-cost-survival bar
comfortably (net Sharpe 0.976/0.924 vs the 0.5 threshold, up from
0.158/0.264 in the undeadbanded predecessor). BTC/USDT now clears every
validator (narrow Sharpe pass at 1.012, same "narrow pass" pattern already
seen for SPY/QQQ elsewhere in this repo). ETH/USDT falls just short on raw
Sharpe (0.946 vs 1.0 threshold) despite passing every other validator
cleanly — a genuine near-miss, not a decisive rejection.

## Accept/Reject

- **QQQ, SPY, BTC/USDT: ACCEPT.** All validators pass for all three.
- **ETH/USDT: REJECT (near-miss).** Sharpe 0.946 narrowly misses the 1.0
  threshold; every other validator (MDD, TC-survival, walk-forward,
  parameter sensitivity) passes cleanly. Consistent with this repo's
  frequent one-symbol-lags-the-other asymmetry pattern (e.g. QQQ-passes-
  SPY-doesn't in many equity strategies here). Not pursued further this
  iteration given diminishing-returns budget; a future iteration could
  retry with a slightly lower target_vol or a per-symbol-tuned config
  specifically for ETH.

This confirms the crypto rescue: full universe now QQQ + SPY + BTC/USDT
accepted for the Parkinson-vol-targeting overlay family (vs the plain,
undeadbanded predecessor's equity-only accept).
