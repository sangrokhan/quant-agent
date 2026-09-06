# Backtest Report: Morning Star Three-Candle Reversal (2026-09-06)

**Hypothesis:** Per QuantifiedStrategies.com's Morning Star candlestick
backtest article: a three-candle bullish reversal pattern -- (1) a tall
bearish candle in a downtrend, (2) a small-bodied candle gapping down from
candle 1, (3) a bullish candle opening below candle 2 and closing above
candle 1's midpoint -- signals a reversal from bearish to bullish momentum.

**Source:** https://www.quantifiedstrategies.com/morning-star-candlestick-pattern/

**Strategy file:** `strategies/2026-09-06_morning_star_reversal.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `small_body_ratio` in {0.35, 0.5, 0.65} x `trend_window` in {30, 50}
  x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high}
- **72 total cells, 0 passed -- pass_fraction = 0.0**
- best_cell == worst_cell (both QQQ, small_body_ratio=0.35, trend_window=30,
  high-vol regime, Sharpe=-0.76) -- meaning every OTHER cell across the
  entire 72-cell grid produced an empty/no-trade slice (no vol-regime bucket
  besides that one high-vol slice on QQQ had even a single trade to compute
  a Sharpe from).

## Step 7 single-config validators (QQQ, small_body_ratio=0.35, trend_window=30, full sample 2019-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | -0.435 | >= 1.0 | FAIL |
| Max drawdown | 0.026 | <= 0.25 | PASS (trivial -- see below) |
| Number of trades (full 7.5-year sample) | **1** | -- | Far too rare to draw any statistical conclusion |

Only ONE Morning Star pattern (matching this strict 3-candle definition)
occurred on QQQ across the entire 2019-2026 sample, and it lost money. The
low MDD is an artifact of near-zero market exposure (flat almost the entire
time), not genuine risk control.

## Decision: REJECT

Decisive rejection on signal-frequency grounds alone: the pattern as
strictly defined (gap-down second candle + midpoint-piercing third candle +
prior downtrend + all-three-candle-size constraints) is far too rare on
daily bars to generate a testable sample, let alone a profitable one. A
looser definition (e.g. dropping the strict gap-down requirement, since
gaps are much rarer on liquid daily-bar equities/crypto than on the
intraday timeframes the pattern was likely designed for) might be worth a
future revisit, but as tested here this is a clean, unambiguous reject.
