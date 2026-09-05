# Volume-Weighted MACD (VW-MACD) Signal-Line Crossover — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_vwmacd_signal_crossover.py`
**Source:** https://www.luxalgo.com/library/indicator/volume-weighted-macd/

## Hypothesis

Rebuild the classic MACD using Volume-Weighted Moving Averages (VWMA)
instead of plain EMAs: VW-MACD = VWMA(fast_span) - VWMA(slow_span), signal =
EMA(VW-MACD, signal_span). High-volume bars drag the lines harder than
thin-volume drift, so a signal-line crossover confirmed by real
participation should be a higher-conviction momentum signal than the
price-only MACD/PPO variants already tested in this repo.

## Grid-test summary (Step 6)

Grid: `fast_span in {8,12}`, `slow_span in {26,35}`, `max_hold_days in
{15,25}`, symbols `{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto),
3 vol-regime terciles, 2018-01-01..2026-09-01.

- **Overall pass fraction:** 13/96 = 13.5%
- **By asset class:** equity 13/48 (27.1%); crypto 0/48 (0%) — decisive
  crypto rejection.
- **By vol regime:** low 9/32 (28.1%), mid 2/32 (6.3%), high 2/32 (6.3%) —
  edge (what little there is) concentrates almost entirely in low-vol
  regimes.
- **Best cell:** QQQ, low-vol, fast_span=12/slow_span=35/max_hold_days=25,
  Sharpe 2.09 (single-tercile cell, not representative of full sample).
- **Worst cell:** SPY, mid-vol, fast_span=12/slow_span=35/max_hold_days=15,
  Sharpe -0.55.

## Single-config validator results (best grid cell config, full sample)

`fast_span=12, slow_span=35, max_hold_days=25`

### QQQ (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.481 | >= 1.0 | ❌ |
| Max drawdown | 32.0% | <= 25% | ❌ |
| TC survival (10bps/trade, 78 trades) | net Sharpe 0.391 | >= 0.5 | ❌ |
| Walk-forward (4 splits) | 4/4 positive (100%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.20 | <= 0.5 | ✅ |

### SPY (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.565 | >= 1.0 | ❌ |
| Max drawdown | 17.8% | <= 25% | ✅ |
| TC survival (10bps/trade, 73 trades) | net Sharpe 0.454 | >= 0.5 | ❌ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.19 | <= 0.5 | ✅ |

Neither symbol clears the Sharpe or TC-survival bar at the grid's best full
sample config. The best full-sample-consistent configs across the 8-cell
param sweep (fast_span=8/slow_span=26/max_hold_days=25) only reach Sharpe
0.74 (QQQ) / 0.78 (SPY) -- still under the 1.0 threshold. The grid's
apparent "best cell" (Sharpe 2.09) is a single low-vol-tercile subset, not
representative of the full-sample behavior.

## Decision

**Reject.** Fails Sharpe ratio and transaction-cost survival on both QQQ
and SPY at every parameter combination tested (best full-sample Sharpe
~0.78, still well under the 1.0 threshold); QQQ additionally fails max
drawdown. Crypto rejected decisively (0/48 grid cells). The volume-
weighting of the moving averages does not appear to meaningfully improve on
the already-tested plain-price MACD/PPO family in this repo.
