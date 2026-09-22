# Backtest Report: Percentile Channel Hysteresis (QQQ)

**Strategy file:** `strategies/2026-09-22_percentile_channel_hysteresis.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-042

## Hypothesis

Per David Varadi's CSSA blog post "A Simple Tactical Asset Allocation
Portfolio with Percentile Channels" (https://cssanalytics.wordpress.com/2015/01/26/a-simple-tactical-asset-allocation-portfolio-with-percentile-channels/,
read via browser_exec since web_extract's DDGS backend cannot fetch article
bodies): rolling percentile rank of close within its own trailing N-day
window; go long when the rank crosses above 0.75, exit when it drops below
0.25 (hysteresis). Source reports a diversified multi-asset TAA portfolio
using this exact signal achieved Sharpe near 2.0 with low drawdown; tested
here as a single-asset long/flat channel signal on QQQ/SPY/BTC-USDT/ETH-USDT.

## Grid Test Summary (Step 6)

- Total cells: 72 (3 window x 2 entry_threshold x 1 rebalance_days, 3 vol
  regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.222 (16/72)
- By asset class: equity 16/36, crypto 0/36 (decisive crypto reject)
- By vol regime: low 12/24, mid 4/24, high 0/24
- Best cell: SPY, window=63/entry_threshold=0.7, low-vol regime, Sharpe 2.56
- Worst cell: QQQ, window=63/entry_threshold=0.8, high-vol regime, Sharpe -1.14
- Best average config: QQQ window=252/entry_threshold=0.7 (or 0.8, identical
  at this rebalance resolution), avg Sharpe 1.298

## Single-Config Validation (Step 7), QQQ, window=252/entry_threshold=0.7/exit_threshold=0.25/rebalance_days=21

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | true | 1.019 | 1.0 |
| Max drawdown | **false** | 0.286 | 0.25 |
| Transaction cost survival (10bps/trade, 5 trades) | true | net Sharpe 1.015 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true | 4/4 splits positive (0.86, 0.18, 2.01, 1.10) | 0.75 |
| Parameter sensitivity | true | relative std 0.315 | 0.5 |

## Outcome: REJECTED

Nearly identical failure mode to this cron trigger's earlier composite
momentum entry (2026-09-22-040): Sharpe barely clears 1.0, but max drawdown
(0.286) decisively fails 0.25 -- both are unconditional monthly-rebalanced
long/cash switches on QQQ with no faster-reacting crash-brake, and both
show the identical drawdown value (0.2856), strongly suggesting the same
underlying COVID-crash drawdown event is the binding constraint for any
monthly-cadence QQQ trend/cash switch tested on this data window. Confirms
(again) this repo's now-repeated finding: monthly-rebalanced absolute-trend
switches on QQQ need a daily-reacting stop-loss overlay (per the
2026-09-22-037->038 rescue pattern) to control MDD; a future iteration
could directly apply that same stop-loss overlay to this percentile-channel
signal.
