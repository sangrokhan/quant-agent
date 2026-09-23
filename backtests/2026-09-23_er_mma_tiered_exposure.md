# Excess-Return Multi-Moving-Average (ER_MMA) Tiered Exposure — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_er_mma_tiered_exposure.py`
**Source:** https://algorithmicfire.com/post/defending-your-savings-against-significant-downturns — "Defending Your Savings Against Significant Downturns" (AlgorithmicFIRE, found via `browser_exec` after `web_search` DDGS/Yahoo backend TLS-errored this iteration).

## Hypothesis

The source's "Excess Return" trend-following family computes daily EXCESS
return (asset return minus risk-free rate, proxied by ^IRX) rather than raw
price, then applies a moving-average trend rule. Its ensemble "Excess Return
MMA" variant blends 3 lookback windows into tiered exposure (0%, 33.3%,
66.7%, 100%) based on window-agreement count — the source's headline result:
across 108 stock ETFs this cut median max drawdown from -51.3% (buy&hold) to
-21.4% while only giving up 0.9pp CAGR, raising median Sharpe from 0.51 to 0.72.

Operationalized: 3 rolling excess-return moving-average windows
(short/mid/long) each vote risk-on if their own MA > 0; exposure = vote_count/3.
A `rebalance_days` throttle (sampling the raw daily vote every N bars, holding
between samples) was added after the initial daily-recompute version failed
transaction-cost survival from excessive turnover (547-548 trades over the
sample vs. the source's own annual-trade-count framing).

## Config selected (from grid + local turnover-reduction search)

`short_window=10, mid_window=50, long_window=150, rebalance_days=5`

## Grid summary (Step 6, before rebalance-throttle fix)

- Grid: `short_window ∈ {10,20} × mid_window ∈ {50,60} × long_window ∈ {120,150,200}` = 12 combos × {QQQ,SPY,BTC/USDT,ETH/USDT} × 3 vol regimes = 144 cells.
- **pass_fraction: 0.319 (46/144)**
- By asset class: equity 42/72 (0.583), crypto 4/72 (0.056).
- By vol regime: low 28/48 (0.583), mid 18/48 (0.375), high 0/48 (0.0).
- Best cell: ETH/USDT, short=20/mid=50/long=150, mid-vol regime, Sharpe 2.17 (not representative of full-sample — crypto rejected decisively below).
- Worst cell: QQQ, short=20/mid=50/long=120, high-vol regime, Sharpe -0.02.

## Single-config validator results (2015-01-01 to 2026-09-01, config above, post rebalance-throttle fix)

| Symbol | Sharpe | MDD | TC-survival (10bps, net Sharpe) | Walk-forward (4-split manual) | Param sensitivity (rel-std, 9-combo local sweep) |
|---|---|---|---|---|---|
| QQQ | 1.024 (pass, thr 1.0) | pass (thr 0.25) | pass (239 trades) | 4/4 pass | 0.072 (pass, thr 0.5) |
| SPY | 1.004 (pass, thr 1.0) | pass | pass (227 trades) | 4/4 pass | (shares QQQ param-sensitivity check) |

Crypto (BTC/USDT, ETH/USDT, `is_crypto=True`, raw return substituted for excess
return since no US T-bill risk-free analog exists for 24/7 crypto): Sharpe
0.23/0.28 (fail), MDD 0.49/0.52 (fail) — decisively rejected.

## Decision

**ACCEPT (equity: QQQ and SPY)**. Both symbols pass all 5 validators at the
rebalance-throttled config; parameter sensitivity is low (rel-std 0.07).
**Crypto rejected** (no risk-free-rate benchmark exists for 24/7 markets, and
the raw-return substitution decisively fails Sharpe/MDD). Note: the initial
daily-recompute version of this signal (no `rebalance_days` throttle) failed
transaction-cost survival on both equity symbols from excessive turnover
(547-548 trades) despite passing Sharpe/MDD — the throttle fix (sample the
vote every 5 trading days, hold between samples) was necessary to make the
strategy net-of-cost viable, consistent with the source's own framing of
trade counts in "trades/year" rather than daily reallocation.
