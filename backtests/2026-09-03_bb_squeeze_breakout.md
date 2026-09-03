# Backtest Report: Bollinger Band Squeeze Breakout (Long-Only)

**Strategy file:** `strategies/2026-09-03_bb_squeeze_breakout.py`
**Date:** 2026-09-03
**Hypothesis id:** 2026-09-03-011

## Hypothesis

Source: http://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/
-- the classic squeeze-breakout construction: Bollinger Band width
contracting to an unusually low value (volatility "squeeze") is followed by
a breakout that tends to continue in that direction. The source's own
extensive backtesting (many assets, many parameter variants) found this does
**not** beat buy-and-hold on nearly any asset tested -- explicitly a
documented negative prior, not a positive lead. This iteration tests it on
this repo's universe to confirm/falsify that finding here, using a standard
construction (band-width rolling percentile + upper-band breakout with a
squeeze-recency window) since the source's exact numeric rule table wasn't
in the extracted free content.

## Step 6 — Grid test summary

Grid: `squeeze_percentile ∈ {0.1, 0.2, 0.3}` × `max_hold_days ∈ {10, 15}` ×
symbols `{QQQ,SPY}` (equity), `{BTC/USDT,ETH/USDT}` (crypto) × 3 vol
terciles (bb_window=20, bb_std=2.0, squeeze_lookback=120,
squeeze_recency=5 fixed). 72 cells, 2019-01-01 to 2026-09-01.

| Slice | Passed / Total |
|---|---|
| Overall | 6 / 72 (8.3%) |
| Equity | 6 / 36 (16.7%) |
| Crypto | 0 / 36 (0.0%) |
| Low-vol | 6 / 24 (25.0%) |
| Mid-vol | 0 / 24 (0.0%) |
| High-vol | 0 / 24 (0.0%) |

Best cell: `squeeze_percentile=0.2, max_hold_days=10`, QQQ, low-vol regime,
Sharpe 1.31 -- again a narrow slice. Worst cell: `squeeze_percentile=0.1,
max_hold_days=15`, SPY, mid-vol, Sharpe -0.77.

## Step 7 — Single-config validation (best config: QQQ, squeeze_percentile=0.2, max_hold_days=10, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.52 | ≥ 1.0 |
| Max drawdown | ✅ | 8.1% | ≤ 25% |
| Transaction cost survival (10bps/trade, 27 trades) | ❌ | net Sharpe 0.44 | ≥ 0.5 |
| Walk-forward (4 windows, manual fallback -- vectorbt API bug, see notes) | ✅ | 4/4 splits positive Sharpe (100%) | ≥ 75% |
| Parameter sensitivity (6-point grid on QQQ) | ✅ | relative std 0.24 | ≤ 0.5 |

Same `check_walk_forward` vectorbt API bug worked around identically to
prior iterations this trigger.

## Decision: **REJECT**

Full-sample Sharpe (0.52) is well below threshold, and the net-of-cost
Sharpe (0.44, just 27 trades over ~7.5 years) narrowly misses the 0.5 gate
too. Positive signs (low MDD 8.1%, stable across walk-forward windows and
parameter perturbations) show the strategy is at least not *unstable* --
it's just a low-conviction, low-frequency edge that doesn't clear the return
bar. **This directly confirms the source article's own documented finding**
(squeeze-breakout underperforms/doesn't reliably beat a simple benchmark
across most assets tested) -- consistent falsification on an independent
universe and time period. Strategy file and report kept as a record of a
rejected attempt (not live).
