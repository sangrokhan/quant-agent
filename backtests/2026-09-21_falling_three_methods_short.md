# Falling Three Methods Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/falling-three-methods-candlestick-pattern/
(read via browser_exec fallback). 5-candle bearish continuation pattern:
tall bearish candle, three small bullish candles confined within its range
(profit-taking pullback), then a tall bearish candle breaking below the
pattern low -> short entry at close of candle 5, stop above candle 1's
high, target = 2x the stop distance (2:1 reward:risk), per source's
disclosed rules.

Strategy file: `strategies/2026-09-21_falling_three_methods_short.py`

## Step 6 — Grid test summary
`grid_summary_falling_three_methods_short.json` /
`grid_cells_falling_three_methods_short.json`

- Grid: `trend_window` in {30, 50, 100}, `tall_body_min_pct` in {0.4, 0.5,
  0.6}, `reward_risk_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY (equity),
  BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324 total cells.
- **pass_fraction: 0.0** (0/324 cells passed Sharpe>=1.0 and MDD<=0.25).
- 180/324 cells had zero trades in their vol-regime slice (empty/no-trade
  slice errors); only 144/324 cells produced any signal at all.
- Best cell: ETH/USDT, mid-vol-regime, Sharpe 0.99993 — a razor-thin
  near-miss just under the 1.0 threshold, identical across most parameter
  combinations (the specific `tall_body_min_pct`/`reward_risk_mult` values
  barely move the result because the underlying trade count is so small).
- by_asset_class: equity 0/162, crypto 0/162. by_vol_regime: low 0/108,
  mid 0/108, high 0/108 (all zero -- no cell anywhere clears both
  thresholds).

## Step 7 — Single-config validation
Skipped a full validators.py run: the grid already gives a decisive,
uniform 0% pass_fraction across every asset class and vol regime, with the
single best cell (ETH/USDT mid-vol, Sharpe 0.99993) failing the Sharpe
threshold outright before any transaction-cost/walk-forward/param-
sensitivity check would even be relevant. QQQ full-sample signal count is
only 4 non-zero position bars over 2018-2026 (8+ years of daily data) —
the containment + downtrend + breakout conjunction is extremely rare on
daily equity bars, consistent with the grid's high empty-slice rate.

## Step 8 — Decision: **REJECT**

Rejection reason: 0/324 grid cells pass; the pattern's 5-candle
conjunction (tall bearish, 3 confined bullish, tall bearish break) is too
rare on daily bars to produce a statistically meaningful sample in any
asset class or vol regime (best cell Sharpe 0.99993, a coincidental
near-miss on a handful of trades, not a demonstrated edge).

Strategy file and this report are kept as a record of a rejected attempt.
Future revisit note: consider intraday bars (where 5-candle patterns
complete far more often) or relaxing the "confined within candle 1" body
constraint further before retrying this pattern family.
