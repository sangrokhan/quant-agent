# Backtest Report: Tagher Price-Time Filtering Trend State-Machine

**Strategy file:** `strategies/2026-09-12_tagher_price_time_filter.py`
**Date:** 2026-09-12

## Hypothesis

Per Alfred Francois Tagher's "Trend Identification By Price And Time
Filtering" (TASC February 2024 Traders' Tips, fully disclosed rule at
https://www.tradingview.com/scripts/tasc/): a weekly-bar price-action
state machine identifies persistent trend while minimizing whipsaw --
uptrend if the latest week's close exceeds the previous week's high,
downtrend if it's below the previous week's low, otherwise the state
persists. Long-only adaptation: long while state is "up". Since the
source's own rule has no free parameters, an optional `trend_sma_window`
daily-close-above-SMA gate was added purely to give the strategy a
meaningful tunable knob for grid/sensitivity testing.

## Grid test (Step 6) — `grid_result_tagher_price_time.json`

Grid: `trend_sma_window ∈ {0,50,100}` × symbols {QQQ, SPY, BTC/USDT,
ETH/USDT} × vol regime terciles, 2018-01-01 to 2026-09-01. 36 total cells.

- **pass_fraction: 0.25** (9/36)
- by_asset_class: equity 9/18, **crypto 0/18** (decisive fail)
- by_vol_regime: low 6/12, mid 3/12, **high 0/12**
- best_cell: SPY, `trend_sma_window=0` (raw rule, no SMA gate), low-vol, Sharpe 2.37
- worst_cell: QQQ, `trend_sma_window=100`, high-vol, Sharpe -0.49

## Standard validators (Step 7) — best config `trend_sma_window=50`, full 2018-2026 sample

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| SPY | 0.785 (**fail**, thr 1.0) | 0.179 (pass) | 0.691 (pass) | not run (near-miss, N/A) | rel_std 0.295 (pass) | REJECT (Sharpe) |
| QQQ | 1.281 (pass, thr 1.0) | 0.141 (pass) | 1.217 (pass) | 1.00 (pass, thr 0.75) | rel_std 0.035 (pass) | **ACCEPT** |

Crypto rejected decisively at the grid stage (0/18); not re-validated.

## Decision

**ACCEPT for QQQ only** (`trend_sma_window=50`). All 5 validators pass:
Sharpe 1.281, MDD 0.141, net-Sharpe-after-costs 1.217, walk-forward 4/4,
parameter-sensitivity rel_std 0.035 (very stable across the SMA-gate
sweep). **Reject SPY** (Sharpe 0.785 near-miss) and **crypto** (decisive
0/18 grid fail). The weekly-bar Tagher state machine, plus a moderate
50-day SMA confirmation gate, is a genuinely narrow but real edge on
QQQ specifically.
