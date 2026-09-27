# Volume Dry-up Bullish-Expansion Breakout (2026-09-28)

**Hypothesis:** LuxAlgo's Volume Dry-up event detector (session with volume
<=0.5x baseline AND contracted range, followed within a short resolution
window by a decisive up-close on >=1.5x baseline volume) marks a
higher-quality long entry than a plain volume-spike breakout, because the
preceding dry-up phase signals sellers stepped away. Source:
https://www.luxalgo.com/library/indicator/volume-dry-up/ (read 2026-09-28
via browser_exec).

## Step 6 grid summary (dryup_threshold x {0.4,0.5,0.6}, expansion_multiple
x {1.5,2.0}, resolution_window x {5,8}; equity QQQ/SPY + crypto BTC/ETH;
vol_regime_splits=3; 144 cells)

- pass_fraction: 0.125 (18/144)
- by_asset_class: equity 1/72, crypto 17/72
- by_vol_regime: low 10/48, mid 3/48, high 5/48
- best_cell: dryup_threshold=0.6, expansion_multiple=1.5,
  resolution_window=5, BTC/USDT, high-vol regime, Sharpe 1.60

## Step 7 full-sample validators (best config: dryup_threshold=0.6,
expansion_multiple=1.5, resolution_window=5, vol_baseline=50,
range_contraction_frac=1.0, max_hold_days=20)

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 6 | -0.32 FAIL | 0.10 PASS | -0.35 FAIL | 0.75 PASS | 122.7 FAIL (near-zero-mean grid) |
| SPY | 2 | -0.68 FAIL | 0.04 PASS | -0.71 FAIL | 1.00 PASS | 0.17 PASS |
| BTC/USDT | 2280 | 0.12 FAIL | 0.50 FAIL | -0.04 FAIL | 0.50 FAIL | 0.05 PASS |
| ETH/USDT | 2710 | 0.23 FAIL | 0.40 FAIL | 0.01 FAIL | 1.00 PASS | 0.35 PASS |

Equity signal is far too sparse (2-6 trades over ~7.5 years) for a
meaningful test even where individual validators technically pass by
chance (walk-forward, param-sensitivity denominators near zero). Crypto
has adequate sample size but decisively fails Sharpe/MDD/TC-survival
(same recurring 1h-bar-vs-daily-logic overtrading pattern as other
strategies this trigger).

## Decision: **REJECT** across all symbols. Equity: signal-scarcity
(2-6 trades, statistically meaningless). Crypto: decisive Sharpe/MDD/
TC-survival fail with adequate sample size, not a scarcity artifact.
Strategy file kept for the record as a rejected attempt.
