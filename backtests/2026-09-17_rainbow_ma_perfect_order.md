# Backtest Report: Rainbow Moving Average "Perfect Bullish Order" Gate

**Strategy file:** `strategies/2026-09-17_rainbow_ma_perfect_order.py`
**Date:** 2026-09-17
**Hypothesis source:** https://www.quantifiedstrategies.com/rainbow-moving-average/ (visited this iteration)

## Hypothesis

The Rainbow Moving Average is a cascade of SMAs: layer1 = SMA(period) of
close, each subsequent layer = SMA(period) of the *preceding layer*
(typically ~10 layers). Source's own disclosed interpretation: "when the
early layer (shorter-period) MAs stay above the subsequent layer
(longer-period) MAs and keep rising further away from the latter, the
market is in an uptrend" ("perfect bullish order"). Implemented long-only:
hold while close > layer1 > layer2 > ... > layerN (strict perfect order),
flat otherwise.

## Grid test (Step 6)

`param_grid={period:[5,9,14], num_layers:[5,8,10]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=27 (25.0%)
- by_asset_class: equity 13/54, crypto 14/54
- by_vol_regime: low 17/36, mid 10/36, high 0/36
- best_cell: SPY low-vol period=9/num_layers=5, Sharpe=1.97

## Single-config validators (Step 7)

Per-symbol best-average-Sharpe-across-regimes configs, run full-period:

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens |
|---|---|---|---|---|---|---|
| QQQ | (5,5) | 0.661 ❌ | 0.123 ✅ | 0.398 ❌ | 1.00 ✅ | 0.335 ✅ |
| SPY | (14,10) | 0.776 ❌ | 0.082 ✅ | 0.636 ✅ | 0.75 ✅ | 0.456 ✅ |
| BTC/USDT | (9,8) | 0.153 ❌ | 0.424 ❌ | -0.007 ❌ | 1.00 ✅ | 0.289 ✅ |
| ETH/USDT | (5,5) | 0.075 ❌ | 0.681 ❌ | -0.052 ❌ | 0.75 ✅ | 0.339 ✅ |

All four symbols decisively fail on Sharpe at the full-period single
config, despite passing grid cells in isolated low/mid-vol slices. The
"perfect order" alignment gate across 5-10 cascaded layers is very
restrictive (few days qualify for entry), leading to low exposure and low
realized return relative to the whipsaws around entry/exit at cascade
boundaries.

## Decision (Step 8)

**Rejected** across all four symbols. Formula and rule correctly
implemented per the source's own disclosed construction and
interpretation, but the alignment gate does not clear this repo's Sharpe
bar for any symbol at a full-period single config.
