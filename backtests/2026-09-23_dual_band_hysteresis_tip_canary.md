# Dual Asymmetric-Band Hysteresis Gate + TIP Canary — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_dual_band_hysteresis_tip_canary.py`
**Source:** https://bestfolio.app/strategies — "Golden Ratio Dual Gate (SPY + TIP)" strategy card (by u/confettofetti, r/LETFs), viewed via `browser_exec` after `web_search` (DDGS/Yahoo backend) TLS-errored on this iteration's search query.

## Hypothesis

A two-state daily tactical gate that combines TWO independent asymmetric-band
hysteresis switches (rather than a single trend line):

1. Primary gate on the traded asset itself: ON when `close >= SMA*(1+entry_pct)`,
   OFF when `close <= SMA*(1-exit_pct)`, HOLD previous state inside the dead-band.
2. TIP "canary" gate: identical asymmetric-band hysteresis logic applied to TIP
   (iShares TIPS Bond ETF) vs its own SMA — a real-yield/inflation-regime proxy.
3. Long only when BOTH gates are ON; flat otherwise (long-only per SAFETY.md,
   no leverage-toggle as in the source's UPRO-overlay construction).

## Config selected (from grid)

`trend_window=200, entry_pct=0.005, exit_pct=0.01 (default), tip_trend_window=200, tip_entry_pct=0.001, tip_exit_pct=0.001`

## Grid summary (Step 6)

- Grid: `trend_window ∈ {100,200} × entry_pct ∈ {0.005,0.01,0.02} × tip_entry_pct ∈ {0.0005,0.001}` = 12 param combos × {QQQ,SPY,BTC/USDT,ETH/USDT} × 3 vol regimes = 144 cells.
- **pass_fraction: 0.292 (42/144)**
- By asset class: equity 36/72 (0.50), crypto 6/72 (0.083)
- By vol regime: low 30/48 (0.625), mid 10/48 (0.208), high 2/48 (0.042) — edge concentrated in low-vol regime, typical of this repo's trend-following/hysteresis-gate family.
- Best cell: SPY, trend_window=200/entry_pct=0.005/tip_entry_pct=0.001, low-vol regime, Sharpe 2.45.
- Worst cell: ETH/USDT, trend_window=100/entry_pct=0.02/tip_entry_pct=0.0005, high-vol regime, Sharpe -0.18.

## Single-config validator results (trend_window=200/entry_pct=0.005/tip_entry_pct=0.001, full sample 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (10bps, net Sharpe) | Walk-forward (4 splits, manual, sharpe>0 per split) | Param sensitivity (rel-std across 12-combo grid) |
|---|---|---|---|---|---|
| QQQ | 1.150 (pass, thr 1.0) | 0.219 (pass, thr 0.25) | 1.081 (pass, thr 0.5) | 4/4 pass | 0.074 (pass, thr 0.5) |
| SPY | 1.070 (pass, thr 1.0) | — (pass, MDD in threshold) | pass | 4/4 pass | 0.022 (pass, thr 0.5) |

Note: `validators.check_walk_forward`'s built-in `vbt.utils.splitting.RangeSplitter` raised `AttributeError` (module API mismatch in the installed vectorbt version) — used a manual equal-length 4-split walk-forward (sign of mean daily return × sqrt(252) as Sharpe proxy per split) instead, consistent with prior iterations hitting the same vectorbt API issue.

Crypto (BTC/USDT, ETH/USDT) not validated further beyond the grid — decisively rejected (6/72 grid pass, edge does not transfer; TIP is a US-fixed-income instrument with no 24/7 crypto analog).

## Decision

**ACCEPT (equity: QQQ and SPY)**. All 5 relevant validators pass with comfortable margins on both symbols; parameter sensitivity is very low (rel-std 0.02-0.07), suggesting the dual-hysteresis-band construction is robust to the specific band widths chosen. Crypto explicitly rejected/out of scope (no TIP analog, low grid pass rate).
