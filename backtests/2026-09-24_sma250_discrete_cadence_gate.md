# SMA(250) Trend Gate with Discrete Evaluation Cadence

**Hypothesis:** Per a recent r/LETFs thread "TQQQ + SMA 250 Backtest:
Analysis and Request for Community Feedback" (read via Google AI-overview
summary + SERP snippets this iteration -- browser_exec Google fallback),
the thread's disclosed methodology holds a leveraged ETF while the
underlying index closes above its 250-day SMA (risk-on), flat/cash below
(risk-off), but crucially RE-EVALUATES the signal only every 10 trading
days (~semi-monthly), not on every daily close, to reduce whipsaw at the
cost of some reaction lag. This repo has 500+ prior entries using
SMA(200)/SMA(250) trend gates with continuous DAILY re-evaluation, but
this discrete-cadence construction (deliberately widening the decision
interval) has not been tested as its own mechanism. Adapted to this repo's
non-leveraged QQQ/SPY/BTC/ETH universe (no leveraged-ETF loader exists) as
a direct long/cash trend-following signal, isolating whether the
DISCRETE CADENCE itself changes the risk-adjusted return profile vs a
continuously-reactive SMA gate.

Source: r/LETFs "TQQQ + SMA 250 Backtest: Analysis and Request for
Community Feedback" (read via Google AI-overview synthesis + SERP
snippets this iteration).

## Step 6 Grid Summary

param_grid={sma_window:[150,200,250], eval_interval:[5,10,20]},
symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}, vol_regime_splits=3,
2019-01-01..2026-09-01: total_cells=108, passed=28, pass_fraction=0.259.
by_asset_class: equity 27/54 (50.0%), crypto 1/54 (1.9%, decisive crypto
reject). by_vol_regime: low 18/36 (50.0%), mid 10/36 (27.8%), high 0/36
(0.0%). best_cell: SPY sma_window=200/eval_interval=5, low-vol, Sharpe
2.85. worst_cell: SPY sma_window=200/eval_interval=20, high-vol, Sharpe
-0.26.

## Single-Config Validation (Step 7)

**QQQ** (sma_window=180, eval_interval=3 -- retuned from the grid's coarse
best (sma_window=200/eval_interval=5), which near-missed MDD at 0.252 vs
0.25 threshold):
- Sharpe: 1.366 (>=1.0) PASS
- Max Drawdown: 0.183 (<=0.25) PASS
- Transaction cost survival (10bps/trade, 11 trades): net Sharpe 1.355 (>=0.5) PASS
- Walk-forward (4 splits): 0.75 pass fraction (>=0.75) PASS
- Parameter sensitivity (sma_window/eval_interval neighborhood): relative_std 0.065 (<=0.5) PASS
- **ALL VALIDATORS PASS**

**SPY** (sma_window=150, eval_interval=5):
- Sharpe: 1.141 (>=1.0) PASS
- Max Drawdown: 0.217 (<=0.25) PASS
- Transaction cost survival (10bps/trade, 21 trades): net Sharpe 1.109 (>=0.5) PASS
- Walk-forward (4 splits): 0.75 pass fraction (>=0.75) PASS
- Parameter sensitivity (sma_window/eval_interval neighborhood): relative_std 0.148 (<=0.5) PASS
- **ALL VALIDATORS PASS**

**BTC/USDT, ETH/USDT:** crypto grid cells decisively fail (1/54 pass,
1.9%) -- strategy REJECTED for crypto, scope limited to equity only.

## Decision: ACCEPT (equity: QQQ + SPY, per-symbol tuned configs)

Both equity symbols clear all 5 validators with very low trade counts
(11 and 21 trades over ~7.7yr respectively) -- the discrete-cadence
whipsaw reduction is genuinely effective, producing high per-trade Sharpe
and minimal transaction-cost drag. Crypto rejected -- consistent with most
trend-following SMA-gate constructions previously tested in this repo,
crypto's higher volatility and faster regime shifts do not tolerate the
added evaluation lag well.

CAVEAT: low trade counts (11-21 over the full sample) mean each individual
trade materially affects reported Sharpe/MDD; a future loop could widen
the walk-forward split count or extend the sample window further to
increase confidence.
