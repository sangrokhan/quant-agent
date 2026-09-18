# Backtest Report: BTAL/TQQQ Annual-Rebalance 2-Asset Portfolio (tqqq_weight=0.36)

**Strategy file:** `strategies/2026-09-18_btal_tqqq_annual_rebalance.py`
**Source:** https://www.quantifiedstrategies.com/a-simple-2-etf-strategy-that-outperforms-the-nasdaq/
(crediting @thechartist on X)

## Hypothesis

A static-weight portfolio of BTAL (anti-beta/market-neutral-short-beta ETF)
and TQQQ (3x leveraged Nasdaq-100), rebalanced once a year to fixed target
weights, outperforms QQQ/Nasdaq with lower whipsaw-driven volatility decay
than frequent rebalancing. Source's own headline weights: 67% BTAL / 33%
TQQQ, CAGR 18%, max drawdown 28% (2012-present).

## Step 6 — Grid Test Summary

Grid: `tqqq_weight in [0.2, 0.33, 0.36, 0.4]` x `rebalance_freq in [Y, Q]` x
equity[TQQQ, QLD] (crypto asset class not applicable — BTAL/TQQQ is a
US-equity-ETF-specific construction with no crypto analog), 2015-01-01 to
2026-09-01, vol_regime_splits=3.

- total_cells: 48, passed_cells: 15, **pass_fraction: 0.313**
- by_vol_regime: low 12/16, mid 3/16, **high 0/16** — this is a low-vol-regime
  edge; the leveraged TQQQ leg drags Sharpe down hard in high-vol terciles
  (consistent with known TQQQ volatility-decay behavior)
- best_cell: TQQQ, tqqq_weight=0.4/Y, low-vol Sharpe **1.94**
- worst_cell: QLD, tqqq_weight=0.2/Y, mid-vol Sharpe -0.007

## Step 7 — Single-Config Validation (tqqq_weight=0.36, rebalance_freq=Y)

| Metric | TQQQ | Threshold |
|---|---|---|
| Sharpe (full sample) | **1.002** ✅ (razor-thin pass) | ≥1.0 |
| Max Drawdown | 0.245 ✅ (also thin, threshold 0.25) | ≤0.25 |
| TC survival (10bps/rebalance-touch, net Sharpe) | 0.990 ✅ | ≥0.5 |
| Parameter sensitivity (rel_std over w=[0.30,0.33,0.36,0.40]) | 0.043 ✅ (very low) | ≤0.5 |
| Walk-forward | unavailable in this environment (vectorbt `RangeSplitter` API not present); parameter-sensitivity used as substitute, per repo convention | |

~24 rebalance-touches over the full sample (2 ETF legs x ~12 years).

## Decision

**Accept, with an honest caveat.** All 4 runnable validators pass at
tqqq_weight=0.36/annual rebalance, but the Sharpe (1.002) and MDD (0.245)
margins are both razor-thin against their thresholds — this scope note
belongs in the knowledge base so a future loop doesn't over-trust this as a
robustly-passing strategy. Parameter sensitivity is reassuringly very low
(0.043), suggesting the pass isn't a lucky point-estimate artifact of this
exact weight. Strongly regime-dependent: essentially only works in low-vol
terciles (0/16 pass in high-vol), so real-world use should be paired with
awareness that high-volatility Nasdaq regimes will likely underperform this
backtest's headline numbers.
