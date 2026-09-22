# Meb Faber Momentum-Breadth Sizing Dial (QQQ/SPY)

**Date:** 2026-09-22
**Source:** https://www.quantifiedstrategies.com/meb-faber-momentum-trend-following-strategy/ (Mebane Faber, 2015 whitepaper / Ned Davis Research)
**Strategy file:** `strategies/2026-09-22_faber_momentum_breadth_sizing_dial.py`

## Hypothesis
Faber's Three-Way Momentum/Trend-Following Model computes an independent
momentum flag (3-month SMA > 10-month SMA) per asset class across
stocks/bonds/gold (SPY/TLT/GLD), then equal-weights across whichever pass.
We cannot replicate a genuine multi-asset reallocating portfolio within the
single-price-series `generate_returns(price_df)` contract, so we
operationalize the cross-asset "momentum breadth" as a fractional [0, 1/3,
2/3, 1] sizing dial applied to whatever asset is being traded (QQQ/SPY in
the grid, requiring breadth_count >= min_breadth for any exposure at all).

## Grid test summary (min_breadth in {1,2}, slow_months in {8,10,12}, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- **72 total cells, 18 passed (pass_fraction = 0.25)**
- By asset class: equity 18/36 passed, **crypto 0/36 passed** (macro
  stocks/bonds/gold breadth signal doesn't transfer to crypto)
- By vol regime: low 12/24, mid 6/24, high 0/24
- Best cell: `min_breadth=1, slow_months=12`, SPY, low-vol, Sharpe 2.59
- Avg equity Sharpe across params/regimes: ~1.0-1.2 (all 6 param combos
  clustered tightly, low sensitivity)

## Single-config validators (fast_months=3, slow_months=10, min_breadth=1 — source's own values)

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.679 — **FAIL** | 0.970 — **FAIL** |
| Max drawdown (<=25%) | 34.1% — **FAIL** | 28.6% — **FAIL** |
| Transaction cost survival (net Sharpe >=0.5 @ 10bps) | 0.648 — pass | 0.943 — pass |
| Walk-forward (4-split, >=75% positive-Sharpe splits) | 100% — pass | 100% — pass |
| Parameter sensitivity (relative std <=0.5) | 0.062 — pass | 0.028 — pass |

## Decision: REJECTED

Full-sample Sharpe AND max drawdown both fail on both QQQ and SPY (SPY MDD
34% vs 25% threshold is a clear miss, not a near-miss). This is the opposite
of the source's own key claim: Faber's actual 3-asset reallocating portfolio
achieves its edge specifically through cross-asset-class DIVERSIFICATION
(spreading capital across stocks/bonds/gold simultaneously, never all-in on
one), which our single-traded-asset sizing-dial reinterpretation cannot
reproduce -- we only ever hold the one traded equity asset itself (QQQ or
SPY), scaled by an external breadth signal, so we inherit that asset's full
idiosyncratic drawdown risk whenever breadth=1 (100% sized). The breadth
dial adds value as a partial risk-reduction overlay (still fails outright)
but is not a substitute for genuine multi-asset allocation. Consistent with
this repo's architectural limitation already noted for other cross-asset
rotation strategies (single price_df contract, no true multi-leg portfolio
support) -- feasibility-adjacent finding, logged as rejected rather than
feasibility-blocked since we did get a runnable proxy and it failed on its
own numeric merits, not purely on infeasibility.
