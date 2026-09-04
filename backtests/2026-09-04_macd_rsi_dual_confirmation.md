# 2026-09-04 MACD + RSI Dual Confirmation — Backtest Report

**Hypothesis** (id `2026-09-04-161`): RSI(14) recovering out of its oversold
zone (crossing back above 30) while the MACD(12,26,9) line is simultaneously
above its signal line marks a higher-conviction long entry. Per
TheForexGeek's RSI & MACD Strategy article (buy rule: RSI around oversold 30
zone + MACD histogram/line above signal line) and QuantifiedStrategies.com's
MACD-and-RSI-Strategy article (73% win rate, 235 trades on SMH 2001-present,
combining MACD+RSI+a third mean-reversion filter — exact numeric rule
paywalled).

**Sources**
- http://www.quantifiedstrategies.com/macd-and-rsi-strategy/ (overview + backtest stats, rule paywalled)
- https://theforexgeek.com/rsi-macd-strategy/ (concrete combo buy/sell rule used here)
- https://quantifiedstrategies.substack.com/p/macd-and-rsi-trading-strategy-rules (paywalled, not used)

**Strategy**: `strategies/2026-09-04_macd_rsi_dual_confirmation.py`

## Grid test (rsi_window∈{10,14}, oversold_threshold∈{25,30}, max_hold_days∈{10,15}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 1, **pass_fraction: 1.0%**
- by_asset_class: equity 1/48 passed; crypto 0/48 passed
- by_vol_regime: low 0/32, mid 1/32, high 0/32
- best_cell: QQQ config unrelated; SPY rsi_window=14/oversold=30/max_hold_days=15, mid-vol regime only, Sharpe 1.017
- worst_cell: QQQ same shared config, low-vol regime, Sharpe -0.79

## Single-config validation (rsi_window=14, oversold_threshold=30, max_hold_days=15) — full sample 2019-2026

| Symbol | Sharpe | Passed (>=1.0) | MDD | Passed (<=0.25) |
|---|---|---|---|---|
| QQQ | 0.511 | NO | 0.016 | YES |
| SPY | 0.644 | NO | 0.011 | YES |

Full-sample Sharpe fails decisively on both equity symbols (not a near-miss),
despite very low MDD (the strategy trades very rarely/holds tiny exposure —
the joint AND condition of RSI-oversold-recovery + MACD-already-bullish is
extremely restrictive, producing a near-flat, low-signal strategy). Grid
pass_fraction of 1% confirms this holds essentially nowhere across the
parameter/asset/vol-regime space; only one single cell (SPY, mid-vol slice)
cleared the bar. Under `suggested_workload=max`, walk-forward/param-sensitivity/
transaction-cost validators were skipped since the strategy failed the
primary Sharpe gate cleanly on both equity symbols and crypto had 0/48 grid
passes.

## Decision: REJECTED

The joint RSI-recovery + MACD-already-bullish AND condition is too
restrictive: it requires MACD to already be in a bullish crossed state at
the exact bar RSI recovers past 30, which happens rarely and produces very
few, weak trades. Distinct failure mode from prior single-indicator MACD
(2026-09-03-013, accepted QQQ via zero-line filter) and RSI (2026-09-04-077,
accepted QQQ/SPY via momentum-threshold use) tests — the AND-combination
does not simply inherit the best of both; it strands entries in a corner of
the parameter space with too little signal.
