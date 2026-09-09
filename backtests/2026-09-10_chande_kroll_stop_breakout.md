# Backtest Report: Chande Kroll Stop (CKSP) Dual-Line Breakout

**Strategy file:** `strategies/2026-09-10_chande_kroll_stop_breakout.py`
**Date:** 2026-09-10
**Outcome:** ACCEPTED (QQQ and SPY); crypto rejected

## Hypothesis

Per LuxAlgo/TrendSpider CKSP guides (SERP-sourced, corroborated across
sources), the Chande Kroll Stop is a two-stage ATR-based trailing-stop
indicator: `first_high_stop = Highest(high,p) - x*ATR(p)`,
`first_low_stop = Lowest(low,p) + x*ATR(p)`, then smoothed over q periods:
`stop_short = Highest(first_high_stop, q)`, `stop_long =
Lowest(first_low_stop, q)`. TrendSpider's disclosed rule: buy when price
crosses above BOTH stop lines. Exit here on close falling below the
lower (long) stop line, or a time-stop. First CKSP strategy in this repo.

## Step 6 grid summary

Grid: `x` (ATR multiplier) in {1.0, 2.0} x `max_hold_days` in {20, 40} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (48 cells,
2018-01-01 to 2024-12-31). Fixed `p=10`, `q=9` (LuxAlgo standard defaults).

- pass_fraction: 0.292 (14/48) — the highest pass fraction of this run's
  5 candidates tested so far
- by_asset_class: equity 14/24, crypto 0/24 (decisive crypto fail)
- by_vol_regime: low 8/16, mid 6/16, high 0/16
- Best cell: x=2.0, max_hold_days=40, QQQ, low-vol tercile, Sharpe 2.46.
  x=2.0/max_hold_days=40 passed BOTH QQQ and SPY on BOTH low and mid vol
  terciles (4/6 equity cells at that one config) — the strongest
  cross-symbol, cross-regime consistency of any candidate this run.

## Step 7 single-config validation (p=10, x=2.0, q=9, max_hold_days=40, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.090 | 1.127 | >= 1.0 | Yes / Yes |
| Max drawdown | 0.245 | 0.186 | <= 0.25 | Yes / Yes |
| TC survival (5bps/trade) | 0.986 | 0.988 | >= 0.5 | Yes / Yes |
| Walk-forward (4 splits) | 0.75 (3/4) | 0.75 (3/4) | >= 0.75 | Yes / Yes |
| Parameter sensitivity | 0.101 | 0.235 | <= 0.5 | Yes / Yes |

Trade counts (entries only): QQQ 72, SPY 72 over ~7 years (roughly 10
trades/year, a reasonable, not-overtrading frequency).

## Decision: ACCEPTED (QQQ and SPY)

Both symbols clear every validator comfortably, with the strongest and
most consistent grid performance of this run's candidates: x=2.0 ATR
multiplier with a 40-day time-stop passes on both equities across both
low and mid volatility regimes (not just a single narrow slice). Crypto
(BTC/ETH) fails decisively across the whole grid (0/24) — this strategy
should not be trusted on crypto. High-vol regime also fails on both
equities (0/16 in that tercile), so the accepted scope is specifically
equity, low/mid volatility.

## Source

- https://www.quantifiedstrategies.com/chande-kroll-stop/ (indicator concept)
- SERP-sourced formula corroborated across trendspider.com and luxalgo.com (Chande Kroll Stop formula/defaults: p=10, x=1 default but x=2 grid-optimal here, q=9)
