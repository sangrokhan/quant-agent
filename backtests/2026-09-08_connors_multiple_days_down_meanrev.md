# Larry Connors Multiple-Days-Down Mean Reversion — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_connors_multiple_days_down_meanrev.py`
**Source:** https://www.quantifiedstrategies.com/multiple-days-up-and-multiple-days-down/
(Larry Connors, *High Probability Trading*, Ch.6, "Multiple Days Down" (MDD)
strategy)

## Hypothesis

Long entry: close > SMA(200) AND close < SMA(5) AND the ETF closed down on
at least `down_days_required` of the trailing `lookback_days` sessions.
Exit: close crosses back above SMA(5). No stop-loss (source's explicit
design). Tested on QQQ/SPY/BTC-USDT/ETH-USDT.

## Grid summary (Step 6)

`param_grid={down_days_required: [3, 4], lookback_days: [4, 5]}`,
`symbols={equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells=48, passed_cells=15, **pass_fraction=0.3125**
- by_asset_class: equity 15/24, crypto 0/24 (decisive crypto rejection)
- by_vol_regime: low 8/16, mid 5/16, high 2/16
- by_symbol: QQQ 6/12, SPY 9/12
- best_cell: SPY mid-vol, down_days_required=4/lookback_days=4, Sharpe 1.83
- worst_cell: QQQ mid-vol, down_days_required=4/lookback_days=4, Sharpe -0.99
  (same param combo passes on SPY mid-vol but fails on QQQ mid-vol — cross-
  symbol inconsistency within the same regime slice)

## Single-config validation (Step 7): down_days_required=4, lookback_days=4

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.196 (FAIL) | 0.745 (FAIL, near-miss) | >= 1.0 |
| Max drawdown | 0.068 (pass) | 0.052 (pass) | <= 0.25 |
| Net Sharpe after 10bps costs | 0.052 (FAIL) | 0.490 (FAIL, near-miss) | >= 0.5 |
| Walk-forward (manual 4-split) | 0.75, 3/4 (pass) | 0.75, 3/4 (pass) | >= 0.75 |
| Parameter sensitivity (4-cell relative std) | 0.400 (pass) | 0.158 (pass) | <= 0.5 |

SPY is a genuine near-miss (Sharpe 0.745, net-Sharpe 0.490 essentially at
threshold) — walk-forward and parameter sensitivity both pass cleanly. The
strategy's low market exposure (source itself reports ~9-28% time-in-market)
means the full-sample daily-return-series Sharpe is diluted relative to the
isolated per-regime grid cells (Sharpe 1.4-1.8), which only look at
sub-periods where the setup actually triggered densely. QQQ is a clearer
miss (Sharpe 0.196).

## Decision: REJECTED (both QQQ and SPY; SPY is a near-miss worth flagging)

Neither symbol clears the Sharpe/net-Sharpe bar on the full sample despite
attractive isolated grid cells and passing walk-forward/param-sensitivity.
Crypto rejected decisively (0/24). SPY's near-miss (0.745 Sharpe, 0.490 net-
Sharpe) is close enough that a future follow-up tightening the entry (e.g.
requiring a deeper RSI-confirmed oversold reading alongside the streak
count, similar to Connors RSI(2) already accepted at 2026-09-03-005) might
push it over the line -- flagged in notes.
