# HMA Mean-Reversion Crossunder — QQQ (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_hma_meanrev_crossunder.py`
**KB id:** 2026-09-22-004

## Hypothesis

Per QuantifiedStrategies.com's own disclosed "Strategy 1" backtest
(https://www.quantifiedstrategies.com/hull-moving-average/): buy SPY at
close when close crosses BELOW the N-day Hull Moving Average, sell when
close crosses back ABOVE the same HMA. The source explicitly finds this
mean-reversion framing outperforms the opposite momentum framing (buy on
cross ABOVE) at every tested N (5,10,25,50,100,200) — CAR 4.86-8.84% vs
0.8-4.62%.

This is the opposite direction from this repo's existing accepted HMA
crossover family (2026-09-04-026 / 2026-09-09-013: long on cross ABOVE
HMA, momentum framing, hma_window=100). Novel: tests the source's own
better-performing mean-reversion (cross-below) framing not yet in this
repo's KB.

## Grid test summary (Step 6)

`param_grid={hma_window:[10,25,50], max_hold_days:[10,20]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 72 cells total.

- Overall pass_fraction: 0.222 (16/72)
- By asset class: equity 16/36 pass, crypto 0/36 pass (decisive crypto reject)
- By vol regime: low 12/24, mid 2/24, high 2/24 (edge concentrated in low-vol regime)
- Best cell: QQQ, hma_window=25, max_hold_days=20, low-vol, Sharpe=1.89
- **QQQ hma_window=10 passed all 3 vol-regime cells** (low/mid/high Sharpe
  1.12/1.38/1.09) — the only (symbol, param) combo robust across all vol
  regimes, so selected as the primary config over the higher-Sharpe but
  vol-regime-fragile hma_window=25 cell.

## Single-config validation (Step 7) — QQQ, hma_window=10, max_hold_days=10

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.108 | ≥1.0 | ✅ |
| Max drawdown | 0.241 | ≤0.25 | ✅ |
| TC survival (10bps/trade, 315 trades) | net Sharpe 0.690 | ≥0.5 | ✅ |
| Walk-forward (4 splits) | 1.0 pass fraction | ≥0.75 | ✅ |
| Parameter sensitivity (hma_window∈{7,10,13,15}) | rel std 0.122 | ≤0.5 | ✅ |

**All 5 validators pass on QQQ.**

## SPY (same params) — for comparison, NOT accepted

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 0.885 | ≥1.0 | ❌ |
| Max drawdown | 0.282 | ≤0.25 | ❌ |
| TC survival | net Sharpe 0.419 | ≥0.5 | ❌ |
| Walk-forward | 1.0 | ≥0.75 | ✅ |
| Param sensitivity | 0.071 | ≤0.5 | ✅ |

SPY fails 3/5 validators — not accepted.

## Decision

**Accept for QQQ only** (hma_window=10, max_hold_days=10). Reject for SPY
and both crypto symbols (BTC/USDT, ETH/USDT decisively failed the grid,
0/36 cells).
