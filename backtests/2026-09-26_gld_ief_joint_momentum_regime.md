# Backtest Report: Joint Gold-Momentum + Treasury-Momentum Regime Filter (2026-09-26)

## Hypothesis
Source: QuantPedia's "Cross-Asset Price-Based Regimes for Gold"
(https://quantpedia.com/cross-asset-price-based-regimes-for-gold/,
browser_exec, own-research 4 Jan 2026). Source's own "most potent" rule:
hold 100% GLD when both GLD's own trailing N-month total return AND IEF's
trailing N-month total return are strictly positive (State 1: "Gold up AND
Treasuries up"); flat otherwise. Source reports this joint 12-month
momentum state dominates all single-signal and other joint-state variants
on Sharpe/Calmar/cumulative return, versus a GLD buy-and-hold baseline.

First joint gold-momentum + treasury-momentum 2-factor regime gate for GLD
in this repo (distinct from ratio-based GLD/TLT gates already tested).

## Full-sample sweep (approximating source's 1/3/6/12-month windows in
trading days: 21, 42, 63, 84, 100, 110, 126, 140, 160, 189, 252)

GLD, 2005-2026:

| momentum_window_days | Sharpe | MDD |
|---|---|---|
| 21 | 0.310 | 0.280 |
| 42 | 0.711 | 0.285 |
| 63 (~3mo) | 0.755 | 0.254 |
| 84 | 0.728 | 0.308 |
| 100 | 0.760 | 0.306 |
| 110 | 0.671 | 0.302 |
| 126 (~6mo) | 0.791 | 0.192 |
| 140 | 0.651 | 0.241 |
| 160 | 0.651 | 0.263 |
| 189 (~9mo) | 0.589 | 0.314 |
| 252 (~12mo, source's favored window) | 0.384 | 0.351 |
| GLD buy-and-hold (reference) | 0.787 | 0.456 |

Best Sharpe found is 0.791 at 126 trading days (~6 months) -- still well
below the 1.0 threshold. Notably the source's own preferred 12-month
window (252 trading days) performs WORST of all tested windows on this
repo's daily-bar reconstruction (Sharpe 0.384), the opposite of the
source's own conclusion that annual is "the most potent version."

## Decision: REJECTED (decisive, no grid test run)

No configuration across an 11-point sweep spanning 1-12 months clears the
1.0 Sharpe threshold; the best (126-day, Sharpe 0.791) is a clear miss, not
a near-miss worth a fine-grained follow-up. The joint 2-factor filter DOES
reduce max drawdown substantially versus GLD buy-and-hold (0.19-0.35 vs
0.456) but at a large cost to risk-adjusted return that this repo's
Sharpe-first acceptance bar doesn't accommodate. Possible explanation: this
repo's data/loaders.py GLD daily-bar reconstruction and the source's
monthly-rebalanced total-return index methodology likely differ materially
(monthly total-return series smooth away noise that daily rebalancing
doesn't); not pursued further given the decisive full-sample gap and time
budget for this iteration.

Source: https://quantpedia.com/cross-asset-price-based-regimes-for-gold/
(browser_exec, own-research, free).
