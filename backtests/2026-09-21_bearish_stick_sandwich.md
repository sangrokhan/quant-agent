# Bearish Stick Sandwich — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/bearish-stick-sandwich-candlestick-pattern/
(read via browser_exec fallback). Mirror of already-rejected Bullish Stick
Sandwich (2026-09-09-036): bullish candle 1 near its high, bearish candle 2
gapping down, bullish candle 3 engulfing candle 2 and matching candle 1's
close (resistance test) in an uptrend. Stop below the pattern's low
(candle 2's low), confirmation = lower close following the pattern.

Strategy file: `strategies/2026-09-21_bearish_stick_sandwich.py`

## Step 6 — Grid test summary
`grid_summary_bearish_stick_sandwich.json` /
`grid_cells_bearish_stick_sandwich.json`

- Grid: `trend_window` in {30, 50, 100}, `close_tolerance_pct` in {0.003,
  0.005, 0.01}, `reward_atr_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY
  (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total
  cells.
- **pass_fraction: 0.028** (9/324 cells). All 9 passing cells: QQQ,
  high-vol-regime only. by_asset_class: equity 9/162, crypto 0/162.
  by_vol_regime: low 0/108, mid 0/108, high 9/108.
- Best cell: QQQ, high-vol, `trend_window=30, close_tolerance_pct=0.01,
  reward_atr_mult=3.0`, Sharpe 1.425, MDD not decisive on its own.

## Step 7 — Single-config validation (QQQ, best-cell params, full sample
2018-2026, no vol-regime gate)

Params: `trend_window=30, close_tolerance_pct=0.01, reward_atr_mult=3.0`.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.431 | >= 1.0 |
| max_drawdown | True | 0.050 | <= 0.25 |
| transaction_cost_survival | **False** | 0.348 net Sharpe (10bps/trade, 19 trades) | >= 0.5 |
| walk_forward (4 splits) | True | 1.0 pass fraction | >= 0.75 |
| parameter_sensitivity | True | rel_std 0.233 | <= 0.5 |

19 trades (10 round-trips) over the full 2018-2026 sample is a reasonable
sample size, and the full-period Sharpe (0.431) is well below threshold --
the grid's high-vol-tercile "pass" cluster (Sharpe 1.425) does not
replicate once the vol-regime restriction is removed, indicating the edge
was concentrated in a favorable subset rather than being a genuine,
broadly-applicable signal.

## Step 8 — Decision: **REJECT**

Rejection reason: fails Sharpe and transaction-cost survival on the
full-period single-config validation (Sharpe 0.431 vs 1.0 threshold), despite
passing walk-forward and parameter-sensitivity. Grid pass_fraction 2.8%
(9/324), confined to QQQ high-vol-regime; not replicated on the unrestricted
full sample.

Strategy file and this report are kept as a record of a rejected attempt.
Note: this confirms the pattern family (Stick Sandwich, matching-close
support/resistance test) does not have an edge in either direction in this
repo -- both the bullish (2026-09-09-036) and bearish (this entry) variants
have now been rejected.
