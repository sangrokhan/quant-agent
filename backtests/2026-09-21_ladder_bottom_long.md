# Ladder Bottom Long — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/ladder-bottom-candlestick-pattern/
(read via browser_exec fallback). 5-candle bullish reversal: 3 progressively
lower bearish candles, a 4th short-bodied bearish candle with upper wick
(weakening momentum), then a 5th bullish candle gapping above candle 4's
body. Source recommends trading it as an end-of-pullback signal within an
uptrend (not a standalone downtrend-bottom call). No specific numeric
stop/target disclosed -- this repo's standard ATR stop/target used.

Strategy file: `strategies/2026-09-21_ladder_bottom_long.py`

## Step 6 — Grid test summary
`grid_summary_ladder_bottom_long.json` / `grid_cells_ladder_bottom_long.json`

- Grid: `trend_window` in {30, 50, 100}, `short_body_max_pct` in {0.25,
  0.35, 0.45}, `target_atr_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY
  (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total
  cells.
- **pass_fraction: 0.083** (27/324 cells passed Sharpe>=1.0 and
  MDD<=0.25). All 27 passing cells are QQQ, low-vol-regime only; Sharpe
  values (1.03/1.29/1.55) are IDENTICAL across all `trend_window` and
  `short_body_max_pct` values within each `target_atr_mult` bucket --
  indicating the underlying trade count is tiny and invariant to those
  parameters, a red flag for a small-sample artifact rather than a real
  parameter-robust edge.
- by_asset_class: equity 27/162, crypto 0/162. by_vol_regime: low 27/108,
  mid 0/108, high 0/108.
- Best cell: QQQ, low-vol, `target_atr_mult=3.0` (any trend_window/
  short_body_max_pct), Sharpe 1.546, MDD 0.009.

## Step 7 — Single-config validation (QQQ, best-cell params, full sample
2018-2026, no vol-regime gate)

Params: `trend_window=50, short_body_max_pct=0.35, target_atr_mult=3.0`.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.251 | >= 1.0 |
| max_drawdown | True | 0.040 | <= 0.25 |
| transaction_cost_survival | **False** | 0.180 net Sharpe (10bps/trade, 8 trades) | >= 0.5 |
| walk_forward (4 splits) | True | 0.75 pass fraction ([T,F,T,T]) | >= 0.75 |
| parameter_sensitivity | True | rel_std 0.164 (across the 27 low-vol-tercile cells only) | <= 0.5 |

Only 8 position changes (4 round-trips) over the full 2018-2026 QQQ
sample -- the pattern's 5-candle conjunction plus uptrend-pullback context
is rare, confirming the grid's own note that the low-vol-tercile "pass"
cluster (identical Sharpe across parameter values) reflects a handful of
lucky trades rather than a genuine, parameter-robust edge. Full-sample
Sharpe of 0.251 is well below the 1.0 threshold.

## Step 8 — Decision: **REJECT**

Rejection reason: fails Sharpe and transaction-cost survival on the
full-period single-config validation. The grid's low-vol-regime "pass"
cluster is a small-sample artifact (only 4 round-trip trades over 8+
years, identical Sharpe across most parameter combinations) rather than a
demonstrated edge -- consistent with the source's own note that this
pattern is "rare and complicated."

Strategy file and this report are kept as a record of a rejected attempt.
