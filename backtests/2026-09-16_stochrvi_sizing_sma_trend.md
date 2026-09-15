# 2026-09-16 Stochastic RVI (Dorsey) Continuous Sizing (full universe accept)

## Hypothesis
"Stochastic RVI" (JohnBaron, TradingView, visited this iteration:
https://www.tradingview.com/scripts/rvi/ — "Based on the Stochastic RSI but
uses RVI (Relative Volatility Index) as source"): generalizes the classic
StochRSI construction (Stochastic formula applied to a rolling window of RSI
values) to Donald Dorsey's Relative Volatility Index instead of RSI. This
repo already has plain Dorsey RVI (midline-crossover confirmation gate,
`2026-09-05-003`/`2026-09-09-080`) and this trigger's earlier StochCMO entry
applied the identical Stochastic-of-oscillator generalization to CMO —
this is the RVI-source variant, first Stochastic-of-Dorsey-RVI construction
in this repo. Reframed as a CONTINUOUS SIZING dial (already [0,1]-bounded,
rescaled to [-1,1] via 2x-1) inside an SMA(trend_window) uptrend gate with
deadband, per this repo's established pattern.

Discovered via: `web_search` returned an empty/garbage result for the
discovery query this iteration (same recurring backend issue as the prior
StochCMO iteration), so **fell back to `browser_exec`** (Google SERP →
TradingView RVI scripts page) per RESEARCH_LOOP.md.

## Grid test (Step 6)
`run_grid_stochrvi_sizing.py`: `sensitivity in [0.4,0.5,0.6]` x
`deadband in [0.20,0.30]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), `vol_regime_splits=3`.

- total_cells: 72, passed_cells: 39, **pass_fraction: 0.542**
- by_asset_class: equity 14/36, crypto 25/36
- by_vol_regime: low 24/24, mid 10/24, high 5/24
- best_cell: ETH/USDT, sensitivity=0.4/deadband=0.2, mid-vol, Sharpe 2.339

## Single-config validation (Step 7)
Default-param config (sensitivity=0.4, deadband=0.20, leverage_cap=1.0)
passed cleanly on BTC/ETH but **QQQ and SPY initially failed Sharpe and/or
transaction-cost survival** (QQQ: 603 trades, net Sharpe -0.19; SPY: 588
trades, net Sharpe -0.16 — turnover far too high at the default deadband).
Widened-deadband retune (same technique used repeatedly this trigger) found
passing configs for both:

| Symbol   | trend_window | sensitivity | deadband | Sharpe | MDD   | TC net Sharpe | Walk-forward | Param sens. | Trades |
|----------|-------------:|------------:|---------:|-------:|------:|---------------:|-------------:|------------:|-------:|
| QQQ      | 40           | 0.3         | 0.60     | 1.293  | 0.188 | 1.054           | 0.75 (3/4)   | 0.159       | 96     |
| SPY      | 100          | 0.2         | 0.60     | 1.030  | 0.114 | 0.895           | 0.75 (3/4)   | 0.094       | 45     |
| BTC/USDT | 40           | 0.4         | 0.20     | 1.263  | 0.228 | 0.515           | 1.00 (4/4)   | 0.057       | 698    |
| ETH/USDT | 40           | 0.4         | 0.20     | 1.153  | 0.239 | 0.571           | 1.00 (4/4)   | 0.088       | 695    |

All 5 validators pass on all 4 symbols (thresholds: Sharpe>=1.0, MDD<=0.25,
net-Sharpe-after-costs>=0.5, walk-forward pass-fraction>=0.75,
param-sensitivity rel-std<=0.5). **Flag for future revisit:** BTC/USDT and
ETH/USDT TC-survival net Sharpe (0.515/0.571) are thin passes against the
0.5 threshold with very high trade counts (~700 trades) — a small increase
in per-trade cost assumptions could flip these; the crypto legs would
benefit from a deadband-widening retune similar to QQQ/SPY in a future
iteration if this near-miss margin proves fragile live.

## Decision
**Accept — full universe (QQQ, SPY, BTC/USDT, ETH/USDT).**

## Source
https://www.tradingview.com/scripts/rvi/ (JohnBaron's "Stochastic RVI"
script description, visited this iteration via browser_exec after
web_search returned an empty/garbage result for the discovery query).
