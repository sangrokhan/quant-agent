# Backtest Report: TSI (True Strength Index) Centerline + Signal-Line Crossover

**Strategy file:** `strategies/2026-09-17_tsi_centerline_signal_crossover.py`
**Date:** 2026-09-17
**Hypothesis source:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/true-strength-index (visited this iteration)

## Hypothesis

William Blau's True Strength Index (TSI) = 100 * doubly-smoothed price
change / doubly-smoothed absolute price change (EMA(long_period) of daily
price change, then EMA(short_period) of that result; default 25/13 per
Blau). Source's own disclosed rules: centerline crossover is "the purest
signal" (bullish when TSI>0), and a signal line (EMA of TSI) "can be applied
to identify upturns and downturns" though "signal line crossovers are quite
frequent and require further filtering". Implemented as: long only when
TSI>0 AND TSI>signal line (both source-disclosed conditions combined).

## Grid test (Step 6)

`param_grid={long_period:[20,25,30], signal_period:[5,7,10]}` (short_period
fixed at Blau's default 13), `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=33 (30.6%)
- by_asset_class: equity 22/54, crypto 11/54
- by_vol_regime: low 28/36, mid 1/36, high 4/36
- best_cell: ETH/USDT mid-vol long_period=30/signal_period=10, Sharpe=2.81

Per-symbol average-Sharpe-across-regimes best configs: QQQ (20,10), SPY
(30,10), BTC/USDT (25,10), ETH/USDT (25,10) — all evaluated at full-period
single-config validators below.

## Single-config validators (Step 7)

### QQQ (long_period=20, short_period=13, signal_period=10)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.071 | 1.0 | ✅ |
| Max Drawdown | 0.119 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 61 trades) | 0.966 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std) | 0.082 | 0.5 | ✅ |

**All 5 pass → accepted.**

### SPY (long_period=30, short_period=13, signal_period=10)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 0.864 | 1.0 | ❌ |
| Max Drawdown | 0.110 | 0.25 | ✅ |
| TC survival | 0.721 | 0.5 | ✅ |
| Walk-forward | 1.00 | 0.75 | ✅ |
| Parameter sensitivity | 0.086 | 0.5 | ✅ |

Near-miss on Sharpe. A local hand sweep over
long_period∈{15,20,25,30,35,40}, short_period∈{7,10,13,17,21},
signal_period∈{3,5,7,10,14,21} found a best of Sharpe=0.980 (MDD=0.109) at
(35,7,14) — still below the 1.0 threshold. **Rejected on SPY** for this
iteration (recorded as a near-miss worth revisiting with a different
overlay, e.g. a trend/regime gate, in a future iteration).

### Crypto (BTC/USDT, ETH/USDT, each symbol's own best-avg config)

| Symbol | Config | Sharpe | MDD | TC net Sharpe |
|---|---|---|---|---|
| BTC/USDT | (25,13,10) | 0.188 (fail) | 0.402 (fail) | 0.015 (fail) |
| ETH/USDT | (25,13,10) | 0.283 (fail) | 0.390 (fail) | 0.083 (fail) |

Decisively rejected: despite one grid cell (ETH mid-vol, different config)
showing a high Sharpe, the full-period single config generates very high
turnover (1845-1895 signal flips) that destroys the edge once transaction
costs are applied — the grid's per-regime best cell does not generalize to
a full-period config.

## Decision (Step 8)

**Accepted** for QQQ only (long_period=20, short_period=13,
signal_period=10, all 5 validators pass). **Rejected** for SPY (near-miss
Sharpe, best hand-tuned config still 0.98<1.0) and crypto (BTC/USDT,
ETH/USDT — decisive Sharpe/MDD/TC-survival fail, high turnover).
