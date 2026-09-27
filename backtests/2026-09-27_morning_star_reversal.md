# Morning Star 3-Candle Reversal — Backtest Report

**Strategy file:** `strategies/2026-09-27_morning_star_reversal.py`
**Date:** 2026-09-27
**Outcome:** REJECTED

## Hypothesis

Source: https://fundedfast.com/learn/candlestick-patterns/morning-star (read
2026-09-27 via browser_exec; citing Bulkowski's Encyclopedia of Candlestick
Charts, 2008).

Morning Star is a 3-candle bullish reversal: candle 1 large bearish, candle
2 small-bodied (indecision), candle 3 bullish closing materially back into
candle 1's body. Bulkowski's large-sample study: 78% reliable as bullish
reversal (rank 12/103), infrequent (rank 66/103). Source's construction:
entry at candle 3's close (aggressive variant), stop below pattern low
(min of candle 1/2 lows), profit target as an R-multiple of initial risk
(source suggests 1.5R-2R). Implemented as described plus a 15-day time-stop
(this repo's convention).

First Morning Star / 3-candle reversal pattern in this repo (0 prior hits).

## Single-config validators (SPY, body_mult=0.75, reclaim_frac=0.6, reward_r_multiple=2.0, max_hold_days=15)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.373 | >= 1.0 | **FAIL** |
| Max drawdown | 0.167 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 34 trades) | 0.297 | >= 0.5 | **FAIL** |
| Walk-forward (4 splits) | 0.75 (3/4 splits Sharpe>0) | >= 0.75 | PASS (borderline) |
| Parameter sensitivity (relative std across body_mult/reclaim_frac/reward_r) | 0.382 | <= 0.5 | PASS |

## Step 6 grid summary (body_mult x reclaim_frac x reward_r_multiple, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- Total cells: 144, passed: 17, **pass_fraction = 0.118**
- By asset class: equity 13/72; crypto 4/72
- By vol regime: **low 16/48, mid 1/48, high 0/48** — edge concentrated
  almost entirely in low-vol regime, fails decisively in mid/high-vol
- Best cell: SPY, body_mult=0.75, reclaim_frac=0.6, reward_r_multiple=2.0,
  low-vol regime, Sharpe 1.535
- Worst cell: QQQ, body_mult=1.0, reclaim_frac=0.6, reward_r_multiple=1.5,
  high-vol regime, Sharpe -1.469 (QQQ fails on ALL grid cells, 0/72 for QQQ
  specifically — only SPY carries the equity pass count)

## Decision: REJECTED

Full-sample Sharpe on SPY's own best grid config (0.373) misses the 1.0
threshold by a wide margin, and net-of-cost Sharpe (0.297) also fails —
the grid's per-vol-regime "passes" are thin (16/48 cells, almost all
low-vol-only) and don't hold up on the full multi-regime sample. Pattern
frequency is inherently low (34 trades over 7.5yr on SPY even with a
relaxed 0.75x ATR body threshold), consistent with Bulkowski's own note
that the pattern is infrequent — likely too few signals for the transaction
cost/Sharpe bar at daily-bar granularity on a single symbol. Not revisited
this iteration; a future loop could try relaxing to a shorter-timeframe
data source (this repo's loaders are daily-only) or combining with the
source's own suggested RSI-divergence/support-level filter to raise
signal quality rather than just frequency.
