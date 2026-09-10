# Backtest Report: BBWP Extreme-Band Exhaustion-Reclaim Mean Reversion

**Strategy file:** `strategies/2026-09-10_bbwp_extreme_band_exhaustion_reclaim.py`
**Date:** 2026-09-10

## Hypothesis

Per Google AI-overview synthesis (TradingView/CrossTrade/TrendSpider/Colibri
Trader/tmgm.com consensus), fetched via `browser_exec` fallback after
`web_search`'s DuckDuckGo backend failed 3 consecutive times this iteration
(TLS `RequestError`/`unexpected-eof` errors, then empty results): during
periods of extreme Bollinger Band Width Percentile (BBWP >= 90 against a
100-bar lookback), a close that punches below the -3 std-dev outer Bollinger
Band and then reclaims back above the -2 std-dev band on the next bar marks
capitulation exhaustion — a mean-reversion long entry — gated by a rising
200-day EMA uptrend filter. Exit at basis (SMA) reversion or a 10-day
time-stop. Distinct from this repo's already-tested BBWP squeeze-BREAKOUT
strategy (`2026-09-07-003`, which fires on LOW BBWP / volatility contraction
preceding a continuation move) — this variant fades the opposite (HIGH BBWP)
tail.

Source: Google search results page for "triple Bollinger band width
percentile mean reversion strategy rules stocks" (AI overview synthesis,
2026-09-10).

## Grid test summary (`validation/grid_test.py::run_strategy_grid`)

- Grid: `bbwp_threshold` in [85, 90, 95] x `max_hold_days` in [5, 10, 15]
- Symbols: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
- vol_regime_splits=3 (low/mid/high realized-vol terciles)
- Period: 2019-01-01 to 2026-09-01
- **Total cells: 108, passed: 0, pass_fraction: 0.0**
- by_asset_class: equity 0/54, crypto 0/54
- by_vol_regime: low 0/36, mid 0/36, high 0/36
- best_cell: bbwp_threshold=90/max_hold_days=10, crypto BTC/USDT, mid-vol tercile, Sharpe 0.202
- worst_cell: bbwp_threshold=85/max_hold_days=5, crypto BTC/USDT, high-vol tercile, Sharpe -0.063

## Single-config validator results (bbwp_threshold=90, max_hold_days=10, full sample)

| Symbol | Sharpe | Passed | Max Drawdown | Passed | Notes |
|---|---|---|---|---|---|
| QQQ | inf (0 trades) | N/A (no signal fired) | 0.0 | trivially passed | Entry condition NEVER triggered over the full 2019-2026 sample |
| SPY | inf (0 trades) | N/A (no signal fired) | 0.0 | trivially passed | Entry condition NEVER triggered over the full 2019-2026 sample |
| BTC/USDT | 0.079 | FAIL (< 1.0) | 0.008 | passed | Only 16 non-zero-return days total; extremely rare/weak edge |

## Decision: REJECT

The entry conjunction (BBWP>=90 AND prior-close<-3SD AND reclaim>-2SD AND
rising-200EMA-uptrend) is so restrictive that it essentially never fires on
equities over a 7.5-year daily sample, and only fires a handful of times on
BTC/USDT with no edge (Sharpe 0.08). The AI-overview's disclosed rule appears
designed for intraday/high-frequency data (the source discusses "scale out"
targets and ATR stops implying much more frequent triggers) and does not
translate to daily-bar equity/crypto testing in this repo. Grid
pass_fraction 0/108 is a decisive rejection, not a near-miss.

Strategy file retained as a record of a rejected attempt (extremely low
trigger frequency at daily-bar resolution); not live.
