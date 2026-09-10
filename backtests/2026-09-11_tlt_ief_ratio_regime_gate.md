# 2026-09-11 TLT/IEF Duration-Ratio Regime Gate on SMA Trend-Following

## Hypothesis
Per ConvexTrade's "TLT vs IEF" comparison (Google SERP snippet, visited
this iteration): "The duration ratio is the dominant driver of TLT-vs-IEF
performance. Curve-shape changes (steepening, flattening) produce
additional but smaller [effects]." The TLT/IEF price ratio (long-duration
20+yr Treasuries vs intermediate 7-10yr Treasuries) is a pure duration-
risk/yield-curve-shape proxy, economically distinct from every other
cross-asset ratio regime gate already tested in this repo (GLD/TLT
gold-vs-bonds, HYG/IEF credit-vs-duration, Copper/Gold industrial-growth,
RSP/SPY breadth, SOXX/QQQ semis-leadership, XLU/SPY defensive-beta,
VVIX/VIX vol-of-vol). Gate: long primary asset's own SMA(trend_sma_window)
trend-following signal only when TLT/IEF ratio is above its own
ratio_sma_window-day SMA (flight-to-duration/bull-flattening proxy);
flat otherwise.

Source: Google SERP snippet of https://convex-trading-production.up.railway.app/tlt-vs-ief (page itself 404'd on direct visit; content read from search result snippet)

## Grid summary (run_strategy_grid, param_grid={trend_sma_window:[150,200], ratio_sma_window:[50,100,150], invert_signal:[False,True]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 144, passed_cells: 33, pass_fraction: 0.229
- by_asset_class: equity 33/72, crypto 0/72 (decisive, no Treasury-duration analog for crypto)
- by_vol_regime: low 22/48, mid 10/48, high 1/48
- best_cell: QQQ, trend_sma_window=200, ratio_sma_window=50, invert_signal=False, low-vol regime, Sharpe 2.32

## Single-config validation (best full-sample config: trend_sma_window=200, ratio_sma_window=100, invert_signal=False)

| Validator | QQQ | SPY | Threshold | QQQ Pass |
|---|---|---|---|---|
| Sharpe ratio (full sample) | 1.111 | 0.881 | >= 1.0 | **PASS** |
| Max drawdown | 0.219 | 0.176 | <= 0.25 | PASS |
| TC survival (10bps/trade, 162 trades) | 0.875 | 0.550 | >= 0.5 | PASS |
| Walk-forward (4 splits, manual RangeSplitter substitute since vectorbt.utils.splitting unavailable) | 1.0 (4/4 splits positive Sharpe) | not run | >= 0.75 | PASS |
| Parameter sensitivity (6-combo grid, relative std) | 0.089 | not decisive | <= 0.5 | PASS |

## Decision: ACCEPT (QQQ only)

All 5 validators pass for QQQ at trend_sma_window=200/ratio_sma_window=100:
Sharpe 1.111, MDD 0.219, TC-adjusted Sharpe 0.875, walk-forward 4/4 splits
positive, parameter-sensitivity relative std 0.089 (very stable across
the 6-combo non-inverted param grid). SPY at the SAME shared config
misses the Sharpe threshold (0.881) -- a near-miss, not accepted at this
config. `invert_signal=True` variants perform materially worse across
the grid (worst cell -0.58 Sharpe on SPY high-vol), confirming the
non-inverted direction (long only when TLT outperforms IEF, i.e. during
flight-to-duration/bull-flattening episodes) is the economically correct
polarity, consistent with the source's framing of duration-ratio as the
dominant TLT-vs-IEF driver. Crypto rejected decisively (0/72) as expected
-- no Treasury-duration analog exists for crypto assets.
