# Backtest Report: Ehlers Cyber Cycle / Trigger-Line Crossover, Trend-Filtered

**Strategy file:** `strategies/2026-09-08_ehlers_cyber_cycle_trend_gate.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per TradingView's "[blackcat] L2 Ehlers Cyber Cycle Trading Strategy"
(https://in.tradingview.com/scripts/cybercycle/, summarizing John Ehlers'
"Cybernetic Analysis for Stocks and Futures" Ch.4, 2004): Cyber Cycle is a
2-pole high-pass-filtered, 4-bar FIR-smoothed oscillator isolating the
dominant short-term price cycle; a "Trigger" line (Cycle delayed one bar)
crossing signals cyclic turns. The source warns raw crossovers carry
multiple bars of lag and can be "exactly wrong" in a strongly trending
market. We gated the bullish Cycle-over-Trigger crossover with a
`trend_window`-day SMA trend filter (only trade cyclic upturns in an
already-favorable trend) plus a `max_hold_days` time-stop, on QQQ/SPY
(equity) and BTC/USDT, ETH/USDT (crypto). First Ehlers Cyber Cycle entry
in this repo.

## Step 6 — Grid test summary

Grid: `trend_window` in {30, 50, 100} x `max_hold_days` in {10, 15, 20},
QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto), 3 vol-regime terciles,
2019-01-01 to 2026-09-01. 108 cells total.

- **pass_fraction: 0.185** (20/108 cells)
- **by_asset_class:** equity 20/54 passed; crypto 0/54 passed (decisive fail)
- **by_vol_regime:** low 18/36; mid 2/36; high 0/36 — edge concentrated in
  low-vol regime, similar pattern to the same-cron-trigger KST near-miss
- **best_cell:** SPY, trend_window=30, max_hold_days=10, low-vol, Sharpe 2.85
- **worst_cell:** QQQ, trend_window=50, max_hold_days=15, high-vol, Sharpe -0.88

## Step 7 — Standard validators (best config: SPY, trend_window=30, max_hold_days=10, full sample 2019-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.816 | >= 1.0 |
| Max drawdown | PASS | 0.160 | <= 0.25 |
| Transaction cost survival (10bps/trade, 138 trades) | **FAIL** | net Sharpe 0.372 | >= 0.5 |
| Walk-forward (4 equal slices, manual fallback) | PASS | 1.0 (4/4 slices positive) | >= 0.75 |
| Parameter sensitivity (9-cell neighborhood) | PASS | relative std 0.288 | <= 0.5 |

## Decision: REJECT

Both Sharpe (0.816 < 1.0) and post-cost Sharpe (0.372 < 0.5) fail on the
full-sample best config. The grid's low-vol-tercile best cell (Sharpe
2.85) doesn't survive to the full sample or mid/high-vol regimes, and the
high per-cycle trade frequency (138 trades over ~7.5 years) means
transaction costs erode the already-marginal gross edge. Crypto rejected
decisively (0/54 grid cells).
