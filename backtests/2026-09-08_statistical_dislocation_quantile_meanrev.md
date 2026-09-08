# Backtest Report: Statistical Dislocation Mean Reversion (Quantile-Gated)

**Strategy file:** `strategies/2026-09-08_statistical_dislocation_quantile_meanrev.py`
**Date:** 2026-09-08
**Status:** ACCEPTED (SPY only, quantile_threshold=0.1, hold_days=5)

## Hypothesis

Per Quantitativo's "A Mean Reversion Strategy from First Principles Thinking"
(https://www.quantitativo.com/p/a-mean-reversion-strate...) and its
follow-up "Murphy's Law" (https://www.quantitativo.com/p/murphys-law): a
"statistically unlikely" price drop is best defined relative to a stock's
OWN trailing return distribution (percentile rank), not a fixed threshold
shared across all names. Implemented at the index-ETF level (this repo's
loaders don't provide S&P 500 constituent-level data): when the
`n_day_window`-day return falls at/below the `quantile_threshold` quantile
of its own rolling `dist_window`-day distribution, AND the asset remains in
a longer-term uptrend (close > SMA(`trend_window`) -- a rough proxy for the
source's own diagnosis that non-fundamental (noise) dislocations, not
fundamentally-driven repricings, are what mean-revert), enter long for a
fixed `hold_days`-day hold.

## Full-sample single-config metrics (quantile_threshold=0.1, hold_days=5 — grid's best cell region)

| Symbol | Sharpe | Max DD | Net Sharpe (5bps/trade) | Walk-forward | Param sensitivity (rel std) | Trades |
|---|---|---|---|---|---|---|
| SPY | **1.104 (PASS)** | **0.110 (PASS)** | **0.938 (PASS)** | **0.75 (PASS)** | **0.192 (PASS)** | 52 |
| QQQ | 0.866 (fail) | 0.251 (fail, need ≤0.25) | 0.777 (pass) | 1.0 (pass) | 0.519 (fail, need ≤0.5) | 59 |

## Step 6 grid summary (quantile_threshold ∈ {0.1,0.2} × hold_days ∈ {3,5,10}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles)

- Total cells: 72, passed (Sharpe≥1.0 & MDD≤0.25): 21 → **pass_fraction 0.292** (strongest grid result of the last several iterations)
- By asset class: equity 21/36 passed; crypto 0/36 (expected — no S&P-constituent-style idiosyncratic dislocation structure on BTC/ETH pairs, and 24/7 trading removes the overnight-gap-driven dislocation mechanism)
- By vol regime: **low 12/24**, mid 8/24, high 1/24 — edge is strongest in low/mid volatility, consistent with the source's own diagnosis that high-vol/fundamental-repricing periods (e.g. November per the source's own case study) break the strategy
- Best cell: quantile_threshold=0.1, hold_days=5, SPY, low-vol regime, Sharpe 3.400
- Worst cell: quantile_threshold=0.2, hold_days=5, SPY, high-vol regime, Sharpe -0.545

## Verdict

**ACCEPTED for SPY only** (quantile_threshold=0.1, hold_days=5) — all 5
validators pass: Sharpe 1.104, MDD 11.0%, transaction-cost-survival net
Sharpe 0.938 (52 round-trip entries over ~7.5yr, low turnover), walk-forward
0.75 (3/4 chunks positive), parameter sensitivity relative_std 0.192 (very
stable across quantile_threshold 0.05-0.2). **QQQ rejected** at the same
config: Sharpe 0.866 misses the 1.0 threshold, MDD 25.1% narrowly breaches
the 0.25 budget, and parameter sensitivity relative_std 0.519 narrowly
fails (QQQ's higher intrinsic volatility likely amplifies both the
drawdown and the parameter instability). **Crypto rejected decisively**
(0/36 grid cells) — consistent with the source's own framing that the edge
comes from idiosyncratic, non-fundamental single-stock/index dislocations
against an uptrend backdrop, a structure that doesn't map cleanly onto
24/7 crypto pairs.

Strategy file and this report are kept as a live accepted strategy scoped
strictly to SPY, quantile_threshold=0.1, hold_days=5 (default params in the
function signature reflect this accepted config).
