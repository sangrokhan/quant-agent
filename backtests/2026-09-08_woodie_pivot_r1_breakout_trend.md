# Backtest Report: Woodie Pivot Point R1 Breakout, Trend-Filtered

**Strategy file:** `strategies/2026-09-08_woodie_pivot_r1_breakout_trend.py`
**Date:** 2026-09-08
**Outcome:** ACCEPTED (QQQ only)

## Hypothesis

Per Swoopr's "Woodie Pivot Points Explained" (https://www.getswoopr.com/learn/technical-analysis/indicators/woodie-pivot-points/),
Woodie's pivot double-weights the prior period's close: `PP = (H+L+2C)/4`,
`R1 = 2*PP - L`. Source describes R1/R2 as "areas where an advance might
stall, reverse, or need to break through with conviction (a 'breakout'
read) to keep extending." We test: long entry when close breaks above
today's R1 (computed from yesterday's OHLC) AND close is above a
`trend_window`-day SMA trend filter (source explicitly warns pivot levels
alone don't account for trend); exit when close falls back below the day's
PP, or a `max_hold_days` time-stop. First Woodie Pivot Point (S/R breakout)
entry in this repo — distinct from Woodie's CCI (an unrelated oscillator by
the same trader).

## Step 6 — Grid test summary

Grid: `trend_window` in {30, 50, 100} x `max_hold_days` in {10, 15, 20},
QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto), 3 vol-regime terciles,
2019-01-01 to 2026-09-01. 108 cells total.

- **pass_fraction: 0.25** (27/108 cells)
- **by_asset_class:** equity 27/54 passed; crypto 0/54 passed (decisive fail)
- **by_vol_regime:** low 18/36; mid 9/36; high 0/36 — edge weakens but is
  not exclusively low-vol (unlike the same-cron-trigger KST near-miss)
- **best_cell:** QQQ, trend_window=30, max_hold_days=10, low-vol, Sharpe 2.76
- **worst_cell:** QQQ, trend_window=100, max_hold_days=10, high-vol, Sharpe -0.42

## Step 7 — Standard validators (best config: QQQ, trend_window=30, max_hold_days=10, full sample 2019-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.271 | >= 1.0 |
| Max drawdown | PASS | 0.184 | <= 0.25 |
| Transaction cost survival (10bps/trade, 240 trades) | PASS | net Sharpe 0.652 | >= 0.5 |
| Walk-forward (4 equal slices, manual fallback) | PASS | 1.0 (4/4 slices positive) | >= 0.75 |
| Parameter sensitivity (9-cell neighborhood) | PASS | relative std 0.123 | <= 0.5 |

SPY spot-check with the same config (trend_window=30, max_hold_days=10,
full sample): Sharpe 0.702, **fails** the 1.0 threshold — this strategy is
QQQ-specific, not a general equity-momentum edge.

## Decision: ACCEPT (QQQ only)

All five validators pass cleanly on QQQ with the best grid config. SPY
fails the headline Sharpe threshold and crypto is rejected decisively
(0/54 grid cells) — scope this strategy to QQQ only. Live in `strategies/`.
