# Price Z-Score Trend-Continuation Regime Filter — Backtest Report

**Strategy file:** `strategies/2026-09-11_price_zscore_trend_continuation.py`
**Date:** 2026-09-11 (id 2026-09-11-039)
**Source:** https://setupalpha.substack.com/p/i-tested-13-momentum-and-oscillator-regime-filters (SetupAlpha Part 2, 2026-06-21)

## Hypothesis

Per SetupAlpha's 1600+ backtest study ranking 13 momentum/oscillator regime filters,
rank #8 (near the paid tier) is a positive price z-score threshold used as a
trend-continuation regime switch: `(C - Avg(C, zLen)) / StdDev(C, zLen) > zThresh/10`.
Distinct from this repo's existing z-score entries, all of which use a NEGATIVE
threshold as a mean-reversion dip-buy signal.

## Grid test summary

- param_grid: `z_window` in {50,100,150,200,250}, `z_threshold` in {0.0,0.3,0.5}
- symbols: equity {QQQ,SPY}, crypto {BTC/USDT,ETH/USDT}
- vol_regime_splits: 3
- **180 total cells, 50 passed (pass_fraction 0.278)**
- by_asset_class: equity 50/90, crypto 0/90
- by_vol_regime: low 30/60, mid 20/60, high 0/60
- best_cell: QQQ, z_window=150/z_threshold=0.3, low-vol Sharpe=2.334

## Single-config validator results (z_window=200, z_threshold=0.3)

| Symbol | Sharpe | Passed | MDD | Passed |
|---|---|---|---|---|
| QQQ | 1.157 | Yes | 0.246 | Yes |
| SPY | 0.860 | No | 0.214 | Yes |

- **Transaction cost survival (QQQ):** 28 trades, 10bps/trade, net Sharpe 1.135 -> **Pass**
- **Walk-forward (QQQ):** 4 splits, per-split Sharpe [1.333, 0.519, 0.547, 0.828], all positive -> pass_fraction 1.0 -> **Pass**
- **Parameter sensitivity (QQQ):** 15-value grid (z_window 150-250 x z_threshold 0.2-0.4), relative_std 0.100 -> **Pass**

## Decision

**Accepted for QQQ only** (z_window=200, z_threshold=0.3). All 5 validators pass. SPY near-miss (best 0.90 at z_window=250/z_threshold=0.0). Crypto rejected decisively (0/90).

## Notes

Confirms SetupAlpha's finding this filter is a stronger-than-average performer, though its
own caveat about parameter sensitivity across their broader study wasn't fully replicated
here (relative_std 0.100 is quite stable in this repo's narrower/QQQ-focused grid).
