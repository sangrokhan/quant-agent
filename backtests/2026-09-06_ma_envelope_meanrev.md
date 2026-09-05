# Backtest Report: Moving Average Envelope Mean Reversion (2026-09-06)

**Strategy file:** `strategies/2026-09-06_ma_envelope_meanrev.py`
**Knowledge base id:** 2026-09-06-106
**Outcome:** REJECTED

## Hypothesis

Moving Average Envelope (20-period SMA +/- fixed percentage bands) mean
reversion: long entry when close crosses back above the lower band after
closing at/below it, exit on close reaching the central MA or a
`max_hold_days` time-stop.

## Sources

- Google AI-overview synthesis (TradingView/Definedge Securities/
  LightningChart): central MA 20-50 period, band offset 2-6%, mean-reversion
  rule = re-entry inside envelope from below, exit at central MA.
- https://www.quantifiedstrategies.com/moving-average-envelope/ — confirms
  20-period SMA / +-5% defaults; SPY backtest disclosed 194 trades, 6.9%
  CAGR, 73% win rate, -15% MDD, 25% time invested (exact entry/exit
  thresholds paywalled). Notes shorter lookback + smaller envelope tends to
  optimize better, and best settings vary by asset.

## Step 6 grid summary (ma_window in [10,20,30], envelope_pct in
[0.03,0.05,0.08], equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 4, **pass_fraction: 0.037**
- by_asset_class: equity 4/54 passed, crypto 0/54 passed
- by_vol_regime: low 1/36, mid 2/36, high 1/36
- best_cell: QQQ, ma_window=10, envelope_pct=0.03, low-vol regime, Sharpe 1.168
- worst_cell: QQQ, ma_window=20, envelope_pct=0.08, mid-vol regime, Sharpe -0.980

Strategy shows only a narrow low-vol-regime QQQ edge; fails broadly across
crypto entirely and across the majority of equity cells too.

## Step 7 single-config validation (QQQ, ma_window=10, envelope_pct=0.03,
max_hold_days=20, full sample 2018-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.067 | >= 1.0 | FAIL |
| Max drawdown | 0.189 | <= 0.25 | PASS |
| Transaction cost survival (10bps, 41 trades) | net Sharpe 0.022 | >= 0.5 | FAIL |
| Walk-forward (4 splits) | pass_fraction 0.5 | >= 0.75 | FAIL |
| Parameter sensitivity (9-cell grid) | relative_std 0.738 | <= 0.5 | FAIL |

## Decision

**REJECTED.** Full-sample Sharpe collapses to near-zero once tested across
the entire 2018-2026 window (grid's best cell of Sharpe 1.17 was a narrow
low-vol-regime fluke on QQQ, not representative of the full sample or of
SPY/crypto). Fails 4 of 5 validators including parameter sensitivity — the
strategy's performance swings wildly (Sharpe -0.98 to +1.17) across nearby
parameter choices, indicating no stable edge, consistent with the source
article's own caveat that "best settings vary from asset to asset" (i.e. it
was likely overfit to their specific backtest window/asset).
