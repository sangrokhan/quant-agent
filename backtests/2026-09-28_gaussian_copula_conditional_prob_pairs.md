# Backtest Report: Gaussian-Copula Conditional-Probability Pairs Trade

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_gaussian_copula_conditional_prob_pairs.py`
**Status:** REJECTED

## Hypothesis

Per Hudson & Thames' "Copula for Pairs Trading: A Unified Overview of Common
Strategies" (https://hudsonthames.org/copula-for-pairs-trading-overview-of-common-strategies/,
read via browser_exec after web_extract's ddgs backend could not extract the
page). Fit a bivariate Gaussian copula on trailing rolling-window
standardized daily log-returns for two legs (QQQ/SPY equity pair, BTC/USDT
vs ETH/USDT crypto pair). Compute each leg's rolling empirical-CDF quantile
(u1, u2) and the Gaussian-copula conditional probability
`C_2|1(u2|u1) = Phi((Phi^-1(u2) - rho*Phi^-1(u1)) / sqrt(1-rho^2))`. Per the
source's own AND-open/OR-exit recommendation: open long (leg A) when
`u1 < b_lo AND C_2|1 > b_up`; exit (OR) when either u1 crosses back above
0.5 or C_2|1 crosses back below 0.5, or a max_hold_days time-stop.

First copula-based entry in this 2600+ entry knowledge base (0 prior
"copula" hits in strategies_index.jsonl).

## Grid test summary (Step 6)

`param_grid`: rank_window in [40,60,90] x b_lo in [0.25,0.35] (b_up=1-b_lo)
x max_hold_days in [10,20]; symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT];
vol_regime_splits=3 (low/mid/high realized-vol terciles).

- total_cells: 144
- passed_cells: 8
- pass_fraction: 0.0556
- by_asset_class: equity 8/72 passed; crypto 0/72 passed (crypto legs
  decisively fail across every parameter combo and every vol regime)
- by_vol_regime: low 0/48, mid 6/48, high 2/48 (low-vol regime completely
  fails; some signal only in mid/high vol)
- best_cell: QQQ, rank_window=60, b_lo=0.35, max_hold_days=10, vol_regime=mid,
  sharpe=2.11 (per-tercile Sharpe, not full-sample)
- worst_cell: BTC/USDT, rank_window=90, b_lo=0.25, low vol, sharpe=-1.29

## Single-config validation (Step 7) — best grid config (QQQ, rank_window=60, b_lo=0.35, b_up=0.65, max_hold_days=10, partner=SPY)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.524 | >= 1.0 | **FAIL** |
| Max drawdown | 0.221 | <= 0.25 | pass |
| Transaction cost survival (10bps/trade, 379 trades) | net Sharpe -0.111 | >= 0.5 | **FAIL** |

Full-sample Sharpe (0.524) is far below the per-tercile "mid vol regime"
cell's Sharpe of 2.11 seen in the grid — the strategy's edge, such as it is,
appears concentrated in specific vol-regime slices and does not generalize
to the full sample. The high trade count (379 over the sample) combined
with a thin edge makes it decisively fail transaction-cost survival even at
a modest 10bps/trade assumption.

## Decision: REJECT

Both the full-sample Sharpe and transaction-cost-survival validators fail
for the grid's best-performing configuration; walk-forward/parameter-
sensitivity were not run given these failures (not needed to reach a
reject decision, consistent with Step 7's "run whichever subset is
relevant" guidance). Crypto legs additionally fail decisively across the
entire grid (0/72 cells), so even a rescue attempt (e.g. adding a trend
filter, per this repo's now-common GARCH/HAR rescue pattern) would need to
separately re-tune the crypto side from scratch. Strategy file is retained
in `strategies/` as a rejected-attempt record per Step 8's guidance (not a
live strategy).
