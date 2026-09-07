# Trend Intensity Index (TII) Breakout with ATR Trailing Stop

**Strategy file:** `strategies/2026-09-08_tii_trend_intensity_breakout.py`
**Source:** https://pinescriptforge.com/strategy/trend-intensity-index

## Hypothesis

Trend Intensity Index (TII) counts the percentage of the last N bars
closing above a moving average (0-100 scale) — directional and
faster-responding than ADX. Per source: TII(30)/SMA(50)/ATR(14); long
entry when TII crosses above 80 AND price above 50-SMA; exit on TII
crossing back below 50 or a 1.5x ATR trailing stop. Source's own 64-symbol
futures backtest showed decisively mixed results by instrument (profit
factor 0.18-2.5), so this iteration tests it specifically on QQQ/SPY/BTC/ETH.

## Grid test summary (Step 6)

`param_grid`: `tii_period in {20,30}`, `sma_period in {50,100}`,
`atr_mult in {1.5,2.5}`; `vol_regime_splits=3`; symbols: equity QQQ/SPY,
crypto BTC/USDT/ETH/USDT.

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 14/48 (0.292) | 10/32 | 4/32 | 0/32 |
| crypto (BTC/ETH) | 0/48 (0.0) | 0/32 | 0/32 | 0/32 |

Best cell: `tii_period=20, sma_period=100, atr_mult=2.5`, low-vol regime,
Sharpe 2.82 (QQQ). Crypto rejected decisively across all 48 cells.

## Single-config validation (Step 7) — best config: tii_period=20, sma_period=100, atr_mult=2.5

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity |
|---|---|---|---|---|---|
| QQQ | ❌ 0.988 (near-miss) | ✅ 0.114 | ✅ 0.972 net Sharpe | ✅ 4/4 | ❌ relative_std 0.967 |
| SPY | ❌ 0.584 | ✅ 0.136 | ❌ 0.562 (barely passes 0.5) | not run | not run |

QQQ is a very close Sharpe near-miss (0.988 vs 1.0) with excellent max
drawdown (0.114, well under budget) and clean walk-forward (4/4 splits
positive), but **parameter sensitivity fails decisively** (relative_std
0.967 vs 0.5 threshold, nearly double the budget) — performance across
the 8-cell equity-only param grid (tii_period x sma_period x atr_mult) is
highly inconsistent, meaning the near-miss Sharpe is likely a
lucky/overfit combination rather than a robust edge. SPY fails Sharpe
outright.

## Decision: **REJECTED** (both symbols; equity near-miss fails on param robustness, not just Sharpe)

## Notes for future iterations

QQQ's isolated best-cell result (Sharpe 0.988, MDD 0.114) looks
attractive on the surface but the param-sensitivity failure (0.967,
nearly 2x the budget) is a strong overfitting signal — do not treat this
as a "just barely missed" near-miss worth re-tuning; the underlying signal
across the parameter surface is inconsistent. Crypto (BTC/ETH) rejected
decisively regardless. If revisiting TII in a future iteration, consider
testing on a wider param grid to map out whether ANY stable region exists,
rather than chasing the current grid's single best cell.
