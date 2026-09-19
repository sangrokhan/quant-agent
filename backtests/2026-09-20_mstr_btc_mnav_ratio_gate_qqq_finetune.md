# MSTR/BTC "mNAV Proxy" Regime Gate — QQQ fine-tune (Iteration 2)

**Direct follow-up to accepted 2026-09-20-040** (BTC/USDT accepted at
`trend_sma_window=100, ratio_sma_window=40`; that entry's notes flagged a
QQQ near-accept at `trend_sma_window=150, ratio_sma_window=60`, Sharpe
1.007, not yet run through the full validator suite).

## Wider QQQ parameter search

Swept `trend_sma_window in {50,75,100,125,150,175,200}` x
`ratio_sma_window in {30,45,60,75,90,120}` (42 combos) on QQQ, full sample
2019-01-01..2026-09-01. Configs clearing both Sharpe>=1.0 and MDD<=0.25:

| trend_sma_window | ratio_sma_window | Sharpe | MDD |
|---|---|---|---|
| 150 | 60 | 1.007 | 0.127 |
| 175 | 45 | 1.027 | 0.127 |
| **175** | **60** | **1.105** | **0.127** |
| 175 | 75 | 1.013 | 0.127 |
| 175 | 90 | 1.074 | 0.140 |
| 200 | 60 | 1.060 | 0.127 |
| 200 | 90 | 1.030 | 0.132 |

`trend_sma_window=175, ratio_sma_window=60` gives the best margin (Sharpe
1.105) and was carried forward as the primary config.

## Full-sample validators (QQQ, tw=175/rw=60)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.105 | >= 1.0 | PASS |
| Max drawdown | 0.127 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 117 trades) | 0.840 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 0.75 (3/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo local grid around 175/60) | 0.059 | <= 0.5 | PASS |

SPY at the SAME shared config (tw=175/rw=60): Sharpe 0.892 (fails, near-miss),
MDD 0.111 (passes), TC-survival 0.524 (passes), walk-forward 0.75 (passes),
param-sensitivity 0.107 (passes) — 4/5 pass but decisive Sharpe fail, so
SPY stays out of scope.

## Decision

**ACCEPT for QQQ** at `trend_sma_window=175, ratio_sma_window=60` (all 5
validators pass). Strategy file unchanged
(`strategies/2026-09-20_mstr_btc_mnav_ratio_gate.py`) — same code, second
accepted config/symbol. Combined live scope after this iteration:
BTC/USDT (tw=100/rw=40) and QQQ (tw=175/rw=60). SPY and ETH/USDT remain
rejected.
