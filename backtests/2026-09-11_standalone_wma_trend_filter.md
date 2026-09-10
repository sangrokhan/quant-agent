# Standalone WMA Trend Filter — Backtest Report

**Strategy file:** `strategies/2026-09-11_standalone_wma_trend_filter.py`
**Date:** 2026-09-11 (id 2026-09-11-038)
**Source:** https://setupalpha.substack.com/p/i-tested-20-trend-based-regime-filters (SetupAlpha, "I Tested 20 Trend-Based Regime Filters", 2026-06-14)

## Hypothesis

Per SetupAlpha's 2,700+ backtest study ranking 20 trend regime filters across SPY/QQQ/Bitcoin,
the plain rule `Regime: C > WMA(C, maLen)` (rank #11 of 20) was one of the more efficient
filters: solid protection, works across all 3 markets, only ~2 points/year drag, and the
source's own comparative finding is that it beats the more elaborate/whipsaw-prone
alternatives ranked worse (TEMA #20, HMA #17, KAMA #13, SMA+/-band #12). Tested here
standalone (no additional confirmation) as its own long/flat trend-following strategy.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- param_grid: `wma_window` in {100, 150, 200, 250, 300}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits: 3
- **60 total cells, 19 passed (pass_fraction 0.317)**
- by_asset_class: equity 19/30, crypto 0/30
- by_vol_regime: low 10/20, mid 9/20, high 0/20
- best_cell: QQQ, wma_window=250, low-vol Sharpe=2.309
- worst_cell: QQQ, wma_window=100, high-vol Sharpe=-0.577

## Single-config validator results (wma_window=250)

| Symbol | Sharpe | Passed | MDD | Passed |
|---|---|---|---|---|
| QQQ | 1.173 | Yes | 0.219 | Yes |
| SPY | 0.837 | No | 0.249 | Yes |

- **Transaction cost survival (QQQ):** 27 trades, 10bps/trade, net Sharpe 1.152 (threshold 0.5) -> **Pass**
- **Walk-forward (QQQ):** 4 equal-size splits, per-split Sharpe [1.207, 0.957, 0.487, 0.963], all positive -> pass_fraction 1.0 -> **Pass**
- **Parameter sensitivity (QQQ):** 7-value grid (wma_window 150-300), relative_std 0.111 -> **Pass**

## Decision

**Accepted for QQQ only** (wma_window=250). All 5 validators pass. SPY is a near-miss across all tested wma_window values (best 0.906 at wma_window=200). Crypto rejected decisively (0/30 grid cells).

## Notes

- Confirms SetupAlpha's own comparative finding: this simple, unconfirmed WMA filter outperforms several more elaborate alternatives already tested/rejected in this repo's history (e.g. TEMA-crossover family, KAMA-crossover family) on a like-for-like full-sample basis.
- SPY near-miss suggests a future loop could retune SPY-specific wma_window or add a light confirmation filter, following this repo's established near-miss-fix pattern.
