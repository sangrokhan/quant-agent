# Backtest Report: ATR-Percentile Volatility-Regime Trend Filter (2026-09-06)

**Hypothesis:** Per QuantifiedStrategies.com's "ATR Percentile-Based Grid
Trading for Crypto Markets" (search-snippet only -- article URL 404s):
volatility regimes classified via ATR Percentile (ATR's percentile rank
within its own trailing distribution): High volatility ATR% >= 70-80, Low
volatility ATR% <= 25-30, Neutral 30-70. The source's grid-trading order-
ladder mechanics don't map onto this repo's single-position framework, so
only the regime-classification rule was adapted: trade a plain trend-
following long ONLY when volatility is in the NEUTRAL band, avoiding both
low-vol ("nothing happening") and high-vol ("chaotic") extremes.

**Source:** Google search snippet for "ATR percentile volatility regime
switching strategy specific rules low high" (quantifiedstrategies.com
article since 404'd).

**Strategy file:** `strategies/2026-09-06_atr_percentile_regime_trend.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `low_threshold` in {25, 30} x `high_threshold` in {70, 80} x symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high}
- **48 total cells, 8 passed -- pass_fraction = 0.167**
- by_asset_class: equity 8/24 (33%), crypto 0/24 (0%)
- by_vol_regime: low 8/16 (50%), mid 0/16, high 0/16
- best_cell: QQQ, low_threshold=25, high_threshold=80, low-vol regime, Sharpe=2.25
- worst_cell: SPY, low_threshold=25, high_threshold=70, high-vol regime, Sharpe=-0.14

Weaker/narrower pass_fraction than the two accepted strategies earlier this
cron trigger (Woodie's CCI TLB 0.306, MAX-effect filter 0.236) -- this
strategy passes ONLY in the low-vol slice, with zero passes in mid or high
vol regimes at all.

## Step 7 single-config validators (best grid combo full-sample: QQQ, low_threshold=25, high_threshold=80)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.756 | >= 1.0 | FAIL |
| Max drawdown | 0.136 | <= 0.25 | PASS |
| Transaction cost survival (net Sharpe, 10bps/trade, 92 trades) | 0.585 | >= 0.5 | PASS |
| Parameter sensitivity (relative std across 4 combos) | 0.117 | <= 0.5 | PASS |
| Walk-forward | not run | -- | `check_walk_forward` broken in installed vectorbt (pre-existing repo-wide tooling gap, not run for any strategy this cron trigger). |

Sensitivity sweep shows Sharpe rising with wider thresholds: best untested-
as-grid's-own-"best_cell" combo (low_threshold=30, high_threshold=80) hits
0.908 full-sample -- still short of 1.0 but closer than the nominal
best-cell config.

## Decision: REJECT (near-miss)

Sharpe misses the 1.0 threshold at every tested full-sample config (best:
0.908 at low_threshold=30/high_threshold=80, untested by the grid's own
per-regime-slice selection). MDD, transaction-cost survival, and parameter
sensitivity all pass. Weaker overall than the cron trigger's two accepted
strategies this run (Woodie's CCI TLB, MAX-effect filter) -- the neutral-
vol-band gate alone isn't a strong enough filter on its own; a future
iteration could try widening thresholds further (low<=35, high<=85) or
combining with an additional confirming signal.
