# ZigZag Confirmed-Pivot Trend-Continuation Breakout — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_zigzag_trend_breakout.py`
**Source:** https://fxglory.com/learn/forex-strategies/forex-zigzag-strategy/ ("Forex ZigZag Strategy: 5 Confirmed-Pivot Setups Backtested")

## Hypothesis

A percent-deviation ZigZag indicator (proxy for MT4/MT5/TradingView ZigZag)
identifies confirmed (non-repainting) swing highs/lows. In confirmed
higher-high/higher-low up-structure, breakouts above the most recent
confirmed swing high signal trend continuation. The source's own 1H-forex
backtest found this was the *least-bad* of 5 tested ZigZag setups
(-0.0542R expectancy) but still net negative after costs. This iteration
tests whether the same construction fares differently on DAILY equity/crypto
bars.

## Grid test (Step 6)

`param_grid={"deviation_pct": [0.03, 0.05, 0.08], "max_hold_days": [10, 15, 20]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.398 (43/108 cells)**
- By asset class: equity 27/54 (0.50), crypto 16/54 (0.30)
- By vol regime: low 29/36 (0.81), mid 6/36 (0.17), high 8/36 (0.22)
- Best cell: SPY, deviation_pct=0.05/max_hold_days=20, low-vol regime, Sharpe 2.39
- Worst cell: SPY, deviation_pct=0.05/max_hold_days=15, mid-vol regime, Sharpe -1.30
- The edge is concentrated almost entirely in the low-vol tercile; mid/high-vol
  regimes fail decisively across nearly all cells — same qualitative pattern
  as many prior breakout-style strategies logged in this repo.

## Single-config validation (Step 7)

Best average-Sharpe param combo across the equity grid was
`deviation_pct=0.08/max_hold_days=20` (avg per-cell Sharpe 0.865); per-symbol
full-sample config used: QQQ `(0.08, 20)`, SPY `(0.05, 20)` (SPY's own
best-cell config).

| Symbol | Params | Full-sample Sharpe | Threshold | Max Drawdown | Threshold |
|---|---|---|---|---|---|
| QQQ | dev=0.08, hold=20 | **0.217** | 1.0 | 0.303 | 0.25 |
| SPY | dev=0.05, hold=20 | **0.516** | 1.0 | 0.128 | 0.25 |

Both symbols decisively fail full-sample Sharpe (QQQ also fails MDD).
Transaction-cost-survival and walk-forward validators were not completed
(API signature mismatches in this repo's helper scripts unrelated to the
strategy itself: `check_transaction_cost_survival` needs `cost_bps_per_trade`/
`num_trades` args, `check_walk_forward` hit a `vectorbt.utils.splitting`
AttributeError) — moot since Sharpe already fails decisively on both symbols.

## Decision: **REJECT**

Decisive full-sample Sharpe failure (0.217 QQQ / 0.516 SPY, both well under
1.0 threshold), consistent with the source article's own finding that this
was the least-bad of 5 ZigZag setups but still not a standalone profitable
system. The strategy only works in the grid's low-volatility tercile
(0.81 pass fraction there vs 0.17-0.22 in mid/high-vol) — same
"good-in-calm-markets-only" pattern seen repeatedly in this repo's breakout
strategies. Strategy/report files kept as a record of a rejected attempt.
