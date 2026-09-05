# DiNapoli Forward-Displaced MA Pullback Continuation — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_dinapoli_displaced_ma_pullback.py`
**Source:** https://www.luxalgo.com/library/concept/displaced-ma/

## Hypothesis

Joe DiNapoli popularized forward-displaced simple moving averages
(canonical "n x d" lines: 3x3, 7x5, 25x5) as dynamic support/resistance
references. Because DMA(t) = SMA_n(t-d), the plotted line is a
deliberately stale reference that "holds still while price pulls back to
it in a trend." Operationalized: in an established uptrend
(close > SMA(200)), a pullback that touches/dips below the displaced MA
and then recovers above it is a continuation-buy entry; exit on a close
back below the displaced MA or a max_hold_days time-stop.

## Config tested (best full-sample cell from 6-cell param sweep)

`dma_window=7, dma_displacement=5` (DiNapoli's canonical "7x5" line)

## Single-config validator results

### SPY (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.057 | >= 1.0 | ✅ |
| Max drawdown | 16.2% | <= 25% | ✅ |
| TC survival (10bps/trade, 84 trades) | net Sharpe 0.811 | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity (6-cell dma_window x dma_displacement grid) | relative std 0.26 | <= 0.5 | ✅ |

**All 5 validators pass on SPY.**

### QQQ (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.914 | >= 1.0 | ❌ (near-miss) |
| Max drawdown | 20.6% | <= 25% | ✅ |
| TC survival (10bps/trade, 88 trades) | net Sharpe 0.746 | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.18 | <= 0.5 | ✅ |

QQQ fails only the Sharpe threshold (0.914 vs 1.0), passing all other
validators -- a genuine near-miss, not a decisive rejection.

## Grid-test summary (Step 6)

Grid: `dma_window in {3,7,25}`, `dma_displacement in {3,5}`, symbols
`{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto), 3 vol-regime
terciles, 2018-01-01..2026-09-01.

- **Overall pass fraction:** 17/72 = 23.6%
- **By asset class:** equity 17/36 (47.2%); crypto 0/36 (0%) — decisive
  crypto rejection.
- **By vol regime:** low 10/24 (41.7%), mid 5/24 (20.8%), high 2/24
  (8.3%) — edge concentrates in low/mid-vol regimes, degrades in high-vol
  (consistent with a pullback-continuation strategy getting whipsawed in
  choppy/high-vol conditions).
- **Best cell:** SPY, low-vol, dma_window=7/dma_displacement=3, Sharpe
  2.12 (single tercile, not full-sample representative -- the winning
  full-sample config is dma_window=7/dma_displacement=5, Sharpe 1.057).
- **Worst cell:** QQQ, high-vol, dma_window=3/dma_displacement=3, Sharpe
  -0.79.

## Decision

**Accept for SPY only** (all 5 single-config validators pass at
dma_window=7/dma_displacement=5, DiNapoli's canonical "7x5" displaced-MA
line). **Reject for QQQ** (Sharpe near-miss, 0.914 vs 1.0 threshold, all
other validators pass) and **reject decisively for crypto** (0/36 grid
cells). Scope this strategy narrowly to SPY, low/mid-vol regimes.
