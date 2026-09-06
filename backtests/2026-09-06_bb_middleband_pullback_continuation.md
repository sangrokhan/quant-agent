# Bollinger middle-band trend-continuation pullback (long-only)

## Hypothesis
Per Money365.Market's Bollinger Bands trend-continuation rule set (quoted
via Google search snippet, inverted here for the long/uptrend case):
"Trend: Middle band sloping [upward]. [Pullback]: Price [pulls back] ...
to the middle band (20-SMA). Entry: [Long]..." Distinct from this repo's
already-accepted "Walking the Bands" strategy (2026-09-05-084, which stays
long while price hugs the UPPER band) by instead entering on a pullback TO
the middle band (dip-buying the moving average in an uptrend).

Source: Money365.Market SERP snippet (direct page fetch 404'd; downtrend
rule read verbatim from the Google search result snippet, inverted for the
long case) -- https://www.money365.market/articles/bollinger-bands-strategy-volatility-trading-made-simple

## Grid test (Step 6)
`param_grid={"slope_window": [5,10,20], "pullback_tolerance": [0.005,0.01]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 72, passed: 10, **pass_fraction: 0.139**
- by_asset_class: equity 10/36, **crypto 0/36**
- by_vol_regime: low 9/24, mid 1/24, high 0/24 (only works in calm markets)
- Best avg-across-regimes config: slope_window=5, pullback_tolerance=0.01
  (SPY avg Sharpe 1.069, best single-cell Sharpe 2.35 low-vol; QQQ avg
  Sharpe only 0.568 at the same config)

## Single-config validation (slope_window=5, pullback_tolerance=0.01, SPY, full sample)
| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** | 0.983 (near-miss) |
| Max drawdown (<=25%) | PASS | 9.7% |
| Transaction cost survival | PASS | net Sharpe 0.842, 60 trades |
| Parameter sensitivity (relative_std <=0.5) | PASS (borderline) | 0.497 |

## Decision: REJECT
Full-sample Sharpe fails, if only narrowly (0.983 vs 1.0 threshold) --
per Step 8, any failing validator is a reject. Also doesn't generalize to
QQQ at the same config (avg Sharpe 0.568) and crypto is rejected
decisively (0/36).

## Notes
- This is a genuine near-miss (arguably worth revisiting with a slightly
  looser Sharpe bar or a SPY-specific refinement in a future iteration),
  but per the strict >=1.0 threshold used consistently in this repo, it is
  rejected as-is.
- Strategy file kept in `strategies/` as a rejected-attempt record.
