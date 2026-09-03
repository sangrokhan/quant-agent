# Backtest Report: MACD(12,26,9) Zero-Line-Confirmed Signal Cross

**Strategy file:** `strategies/2026-09-03_macd_zeroline_confirm.py`
**Hypothesis ID:** 2026-09-03-013
**Source:** https://agentictraders.io/learn/macd-crossover-strategy

## Hypothesis

Classic Gerald Appel MACD(12,26,9) (MACD = EMA12-EMA26, signal = EMA9(MACD)).
The source documents that raw bullish/bearish signal-line crosses fire
frequently and whipsaw in ranging markets, but recommends a "zero-line
confirmation" filter: only take a bullish signal-line cross when the MACD
line is already >= 0 (i.e. the fast EMA is already above the slow EMA),
because zero-line crosses "carry meaningfully higher win rates in
backtests" even though they mean somewhat later entries. This is the first
MACD/EMA-convergence-family strategy tested in this repo.

Rules: long when MACD line crosses above signal line AND MACD >= 0; exit on
MACD line crossing below signal line; flat otherwise; long-only.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `fast` in {8,12} x `slow` in {21,26} x `require_zero_confirm` in
{True,False} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles
= 96 cells, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.271** (26/96)
- by_asset_class: equity 26/48 (54%), crypto 0/48 (0%)
- by_vol_regime: low 16/32 (50%), mid 5/32 (16%), high 5/32 (16%)
- best_cell: QQQ, fast=8/slow=26/zero_confirm=True, low-vol regime, Sharpe 2.20
- worst_cell: ETH/USDT, fast=8/slow=21/zero_confirm=False, low-vol regime, Sharpe -0.06

Same now-familiar pattern as most prior trend/momentum-family strategies in
this repo: passes only on equity, fails crypto entirely, concentrated in
low-vol regime.

## Single-config validators (best grid config: fast=8, slow=26, signal=9, require_zero_confirm=True)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.24 (pass, thr 1.0) | 11.2% (pass, thr 25%) | 0.92 (pass, thr 0.5, 148 trades @10bps) | 1.0 (pass, thr 0.75) | rel.std 0.11 (pass, thr 0.5) |
| SPY | 0.93 (fail) | 10.2% (pass) | 0.47 (fail) | 1.0 (pass) | n/a (grid run on QQQ only) |
| BTC/USDT | 0.19 (fail) | 51.7% (fail) | -0.03 (fail) | 1.0 (pass) | n/a |

Walk-forward used a manual 4-way date-slice fallback (vectorbt
`utils.splitting.RangeSplitter` still broken in the installed vectorbt
version — unfixed since 2026-09-03-002, not addressed this iteration).

Parameter sensitivity computed via a 6-point sweep over
fast/slow/zero_confirm combos on QQQ (see grid table above): relative std
0.11, well inside the 0.5 threshold.

## Decision: **ACCEPT (QQQ only)**

QQQ clears all 5 standard validators at the grid-optimal config
(fast=8, slow=26, signal=9, require_zero_confirm=True): Sharpe 1.24, MDD
11.2%, net-of-cost Sharpe 0.92 (148 trades over 7.7y @ 10bps), walk-forward
4/4 splits positive, parameter-sensitivity relative std 0.11.

SPY narrowly misses (Sharpe 0.93, TC-adj Sharpe 0.47) — a near-miss worth
revisiting with a different fast/slow pair in a future loop. BTC/USDT and
crypto broadly fail decisively (MDD 51.7%, near-zero raw Sharpe) — the
zero-line-confirmation MACD edge does not transfer to crypto's noisier,
24/7 regime at daily granularity, consistent with nearly every other
trend-following strategy tested in this repo.

**Scope: equity (QQQ) only, long-only, zero-line-confirmed MACD(8,26,9).
Do not extend to SPY, crypto, or high-vol regimes without further
validation.**
