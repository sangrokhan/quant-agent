# Backtest Report: Unfilled Gap-Down + RSI(10)<threshold Fixed-Hold Swing — REJECTED

**Strategy file:** `strategies/2026-09-11_unfilled_gap_rsi_swing.py`
**Hypothesis ID:** 2026-09-11-084

## Hypothesis

Per QuantifiedStrategies.com's "Unfilled Gap Trading Strategies" article
(https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/,
visited this iteration): an "unfilled gap down" (today's high never
trades back into yesterday's range, i.e. high < yesterday's low) combined
with an RSI(10) reading below 50 marks the best gap-down setups per the
source's own ES-futures study (2010-2021). Enter at the close of the
unfilled-gap-down day, hold for a fixed x-day period, exit at the close.
This repo's implementation used a slightly wider RSI threshold grid
(40/50/60) since the source's own disclosed insight was directional
("below 50 is better") rather than a single precise cutoff.

## Single-config validator results (QQQ, rsi_threshold=60.0, hold_days=10; 2016-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.841 | ≥ 1.0 |
| Max drawdown | ❌ | 0.260 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 137 trades) | ✅ | net Sharpe 0.708 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | ✅ | 4/4 splits positive | ≥ 0.75 pass fraction |
| Parameter sensitivity (9-combo grid: rsi_threshold∈{40,50,60} × hold_days∈{3,5,10}) | ❌ **decisive fail** | relative_std 0.775 | ≤ 0.5 |

**Decision: REJECTED** — fails Sharpe, MDD, AND parameter sensitivity on
the single best-performing config identified by the grid. The parameter
sensitivity failure is especially notable: Sharpe across the 9-combo grid
ranges from 0.047 (rsi_threshold=50, hold_days=3) to 0.841
(rsi_threshold=60, hold_days=10) — a >17x spread — meaning the strategy's
apparent edge is almost entirely a function of using the LOOSEST possible
RSI filter (60, barely filtering anything) combined with the LONGEST hold
period tested, which looks like the strategy is really just capturing
generic upward drift over a 10-day hold with a nearly-no-op RSI filter,
not a genuine RSI-gated gap-reversal edge as hypothesized.

## Step 6 grid summary (param_grid rsi_threshold=[40,50,60] x hold_days=[3,5,10], symbols equity=[SPY,QQQ] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2016-01-01 to 2026-09-01)

- total_cells=108, passed=20, **pass_fraction=0.185**
- by_asset_class: equity 20/54 pass, crypto **0/54 decisive reject**
- by_vol_regime: low 16/36, mid 4/36, **high 0/36 decisive fail**
- best_cell: QQQ, rsi_threshold=50, hold_days=10, low-vol, Sharpe 2.30
- worst_cell: QQQ, rsi_threshold=50, hold_days=5, mid-vol, Sharpe -0.75

## Notes

- Source: https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/
  (visited this iteration, first read of this URL).
- Novel construction for this repo: uses the source's own stricter
  "unfilled gap" definition (today's high < yesterday's low, not an
  open-vs-prior-close percentage threshold), enters at the CLOSE of the
  gap day (not the open), and uses a FIXED holding period with no
  early-exit logic — distinct from every other gap strategy in this repo
  (2026-09-08-171 multi-day-fill, gapdown_ibs_rsi_swing open-entry, etc.).
- The extreme parameter sensitivity (best config uses the loosest RSI
  filter and longest hold) strongly suggests the apparent edge is mostly
  generic equity upward drift over a 10-trading-day window rather than a
  genuine gap+RSI-specific signal — a useful negative-result confirmation
  that this particular "unfilled gap" definition doesn't add value beyond
  what a plain buy-and-hold-for-10-days rule would already capture.
