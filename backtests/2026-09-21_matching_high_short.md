# Matching High Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/matching-high-candlestick-pattern/
(read via browser_exec fallback). 2-candle bearish reversal (mirror of
Matching Low, already tested in this repo): long bullish candle 1, smaller
bullish candle 2 opening below candle 1's close but closing at/near the
same level (matching closes = resistance test), scoped to a downtrend-rally
context per source's own explicit direction guidance. Confirmation:
3rd candle bearish, closing below the pattern low. Stop above the pattern
high; no numeric target disclosed.

Strategy file: `strategies/2026-09-21_matching_high_short.py`

## Step 6 — Grid test summary
`grid_summary_matching_high_short.json` / `grid_cells_matching_high_short.json`

- Grid: `trend_window` in {30, 50, 100}, `match_tolerance_pct` in {0.002,
  0.003, 0.005}, `target_atr_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY
  (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total
  cells.
- **pass_fraction: 0.009** (3/324 cells). All 3 passing cells: QQQ,
  mid-vol-regime, `trend_window=50, target_atr_mult=3.0` (across
  match_tolerance_pct values), Sharpe 1.114.
- by_asset_class: equity 3/162, crypto 0/162. by_vol_regime: low 0/108,
  mid 3/108, high 0/108.

## Step 7 — Single-config validation (QQQ, best-cell params, full sample
2018-2026, no vol-regime gate)

Params: `trend_window=50, match_tolerance_pct=0.005, target_atr_mult=3.0`.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.130 | >= 1.0 |
| max_drawdown | True | 0.117 | <= 0.25 |
| transaction_cost_survival | **False** | 0.079 net Sharpe (10bps/trade, 14 trades) | >= 0.5 |
| walk_forward (4 splits) | True | 0.75 pass fraction ([F,T,T,T]) | >= 0.75 |
| parameter_sensitivity | True | rel_std 0.272 | <= 0.5 |

14 trades (7 round-trips) over the full 2018-2026 sample. Full-period
Sharpe (0.130) is far below threshold, confirming the mid-vol-regime
grid "pass" cluster (Sharpe 1.114) is a slice-concentration artifact, not
a genuine broad edge.

## Step 8 — Decision: **REJECT**

Rejection reason: fails Sharpe and transaction-cost survival on the
full-period single-config validation (Sharpe 0.130 vs 1.0 threshold).
Grid pass_fraction 0.9% (3/324), confined to one QQQ mid-vol-regime
slice that doesn't replicate on the unrestricted full sample.

Strategy file and this report are kept as a record of a rejected attempt.
Note: this completes testing of both directions of the Matching
High/Low pattern family in this repo.
