# Backtest report: Gann 3-bar swing structure trend-following

**Strategy file:** `strategies/2026-09-10_gann_3bar_swing_trend.py`
**Knowledge base id:** 2026-09-10-046
**Outcome: REJECTED** (decisive Sharpe fail across the full parameter grid; crypto 0/54)

## Hypothesis

Per justmarkets.com's Gann Swing Lines guide (visited this iteration,
https://justmarkets.com/trading-articles/forex/what-are-the-gann-swing-lines):
a 3-bar swing is an UPSWING when the 3rd bar has a higher high AND higher
low than BOTH the 1st and 2nd bars (mirror rule for a DOWNSWING). A
confirmed series of upswings marks a short-term uptrend; a downswing signals
a potential reversal. Operationalized as: long entry on a swing-state flip
to "up" while price is above SMA(trend_window); exit on flip to "down",
trend break, or a time-stop. Distinct raw-bar-pattern swing-structure
construction from this repo's existing Gann HiLo Activator strategies
(2026-09-04-128, 2026-09-05-017), which use a stepped SMA-of-high/SMA-of-low
trailing line rather than raw 3-bar pattern matching.

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = trend_window∈{20,50,100} ×
max_hold_days∈{10,20,30}, symbols = {equity: QQQ/SPY, crypto:
BTC/USDT/ETH/USDT}, vol_regime_splits=3, 2018-01-01 to 2024-12-31.

- **total_cells:** 108
- **passed_cells:** 27
- **pass_fraction:** 0.25
- **by_asset_class:** equity 27/54; **crypto 0/54 (decisive fail)**
- **by_vol_regime:** low 18/36, mid 9/36, **high 0/36 (decisive fail)**
- **best_cell:** trend_window=20, max_hold_days=10, SPY, low-vol tercile, Sharpe=2.542 (single favorable slice)

## Full-sample single-config sweep

| trend_window | max_hold_days | QQQ Sharpe | SPY Sharpe | BTC Sharpe | ETH Sharpe |
|---|---|---|---|---|---|
| 20 | 10 | 0.896 | 0.763 | 0.088 | 0.136 |
| 20 | 20 | 0.875 | 0.723 | 0.085 | 0.132 |
| 20 | 30 | 0.875 | 0.703 | 0.086 | 0.127 |

**Best full-sample config (trend_window=20, max_hold_days=10): QQQ
Sharpe=0.896, SPY Sharpe=0.763** — both decisively below the 1.0 threshold
across every parameter combination tested (no config comes close to
clearing 1.0 on SPY; the gap is far larger than a "near-miss"). Crypto is
categorically unusable (best BTC/ETH Sharpe found was 0.136).

## Decision

**Rejected — decisive.** Unlike some of this cron trigger's other
near-miss iterations, this hypothesis misses the Sharpe threshold by a
wide margin on both equity symbols at every parameter combination tested,
and crypto is categorically unusable. The raw 3-bar swing-pattern
construction appears to generate too many false-positive trend flips
(noise-sensitive) compared to the smoother SMA-based Gann HiLo Activator
already in this repo's knowledge base.
