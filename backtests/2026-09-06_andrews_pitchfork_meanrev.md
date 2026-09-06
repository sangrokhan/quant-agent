# Andrews Pitchfork median-line mean-reversion (long-only)

## Hypothesis
Andrews' Pitchfork anchors a median line and two parallel tine lines through
three alternating swing pivots (A-B-C). Per LuxAlgo's construction spec
("three most recent confirmed alternating swing pivots become A, B and C...
a thicker median line from the handle through the B-C midpoint, parallel
tines through B and C") and LiteFinance's mean-reversion trading rule ("Exit
the position at the median line or the opposite boundary of the channel"):
for a bullish Low-High-Low pivot triple, long entry when price touches/dips
to the lower tine (through C) and bounces back above it; exit at the median
line, on stale pivots, or a max_hold_days time-stop.

Sources:
- https://www.luxalgo.com/library/indicator/andrews-pitchfork/ (construction)
- https://www.litefinance.org (mean-reversion trading rule via SERP snippet)

First Andrews-Pitchfork strategy in this repo -- distinct from Fibonacci
retracement (fixed retracement fraction, not a sloped forward-projected
channel), Regression Channel (OLS-fit, not pivot-anchored), and Donchian/
Keltner (fixed-width, non-sloped channels).

## Grid test (Step 6)
`param_grid={"swing_length": [7,10,15], "tine_tolerance": [0.01,0.02]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 72, passed: 7, **pass_fraction: 0.097**
- by_asset_class: equity 7/36, **crypto 0/36**
- by_vol_regime: low 2/24, mid 0/24, high 5/24 (no consistent regime pattern)
- best_cell: swing_length=15, tine_tolerance=0.01, QQQ, high-vol, Sharpe 2.31
- worst_cell: same params, SPY, mid-vol, Sharpe -1.12 (doesn't generalize
  even across the two equity tickers at the same config)

## Single-config validation (swing_length=15, tine_tolerance=0.01, QQQ, full sample)
| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** | 0.876 |
| Max drawdown (<=25%) | PASS | 5.8% |
| Transaction cost survival | PASS | net Sharpe 0.828, but only **11 trades** over 7.7yr |

## Decision: REJECT
Decisive: only 9.7% grid pass fraction, crypto 0/36 outright, no consistent
by-asset-class or by-vol-regime pattern (best cell is high-vol for QQQ but
the same config is a loss on SPY), and the single best-scoring config
produces only 11 trades over 7.7 years and fails the primary Sharpe
threshold on the full QQQ sample (0.876 vs 1.0) -- both a sparse-signal
artifact and a genuine Sharpe miss.

## Notes
- Strategy file kept in `strategies/` as a rejected-attempt record.
