# Backtest Report: Ehlers Super Smoother Slope + Price-Above-Line Trend Filter

**Strategy file:** `strategies/2026-09-17_ehlers_super_smoother_trend.py`
**Date:** 2026-09-17
**Hypothesis source:** https://alphax.trading/dictionary/ehlers-super-smoother (visited this iteration)

## Hypothesis

John Ehlers' Super Smoother: 2-pole Butterworth recursive digital filter
(a1=exp(-1.414π/period), b1=2·a1·cos(1.414·180/period), c2=b1, c3=-a1²,
c1=1-c2-c3, SS[t]=c1·(price[t]+price[t-1])/2+c2·SS[t-1]+c3·SS[t-2]), a
minimal-lag alternative to a standard moving average. Source's own
disclosed execution rules: "Enter a long position when the Super Smoother
slope turns positive and price closes above the smoothed line. Exit long
positions when the Super Smoother slope flattens or turns negative."
Implemented exactly as disclosed: long while slope(SS) > 0 AND close > SS.

## Grid test (Step 6)

`param_grid={period:[10,20,30]}`, `symbols={equity:[QQQ,SPY],
crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- total_cells=36, passed=12 (33.3%)
- by_asset_class: equity 7/18, crypto 5/18
- by_vol_regime: low 11/12, mid 0/12, high 1/12
- best_cell: QQQ low-vol period=30, Sharpe=2.15

Per-symbol average-Sharpe-across-regimes best configs: QQQ (30, avg 1.07),
SPY (30, avg 1.22), BTC/USDT (30, avg 1.17), ETH/USDT (20, avg 1.18).

## Single-config validators (Step 7)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | period=30 | 0.887 ❌ | 0.231 ✅ | 0.726 ✅ | 0.75 ✅ (marginal) | 0.162 ✅ | **near-miss reject** |
| SPY | period=30 | 1.248 ✅ | 0.126 ✅ | 1.024 ✅ | 1.00 ✅ | 0.348 ✅ | **accept** |
| BTC/USDT | period=30 | 0.179 ❌ | 0.654 ❌ | -0.022 ❌ | 1.00 ✅ | 0.099 ✅ | **decisive reject** |
| ETH/USDT | period=20 | 0.170 ❌ | 0.544 ❌ | -0.026 ❌ | 1.00 ✅ | 0.089 ✅ | **decisive reject** |

QQQ is a near-miss (only Sharpe fails, 0.887 vs 1.0; walk-forward is a
marginal pass at exactly the 0.75 threshold). SPY passes all 5 validators
cleanly. Crypto (BTC/USDT, ETH/USDT) decisively rejected: the slope+
price-above-line condition whipsaws constantly on crypto's higher daily
volatility (3699-4774 signal flips), producing near-zero net Sharpe after
costs and MDD ~2-2.6x the cap.

## Decision (Step 8)

**Accepted** for SPY only (period=30, all 5 validators pass). **Rejected**
QQQ as a near-miss (Sharpe 0.887, all other validators pass — worth
revisiting with a vol-scaling or hysteresis-band overlay in a future
iteration) and crypto (BTC/USDT, ETH/USDT — decisive Sharpe/MDD/TC fail
from high turnover).
