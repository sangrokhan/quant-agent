# Backtest Report: Heikin Ashi Consecutive-Color Momentum + EMA(100) Trend Filter

**Strategy file:** `strategies/2026-09-04_heikin_ashi_momentum.py`
**Knowledge base id:** 2026-09-04-045

## Hypothesis

Per a Google AI-overview synthesis (PyQuantLab Medium article et al.):
Heikin Ashi candles (smoothed OHLC transform) reduce noise. Trend-follow
entry: price above EMA(trend_window) AND N consecutive same-color
(bullish) Heikin Ashi candles signals strong directional momentum; exit
on the first opposite-color HA candle (color-flip exit, simplified from
the source's compound no-wick+ATR-trail rule).

Source: Google AI-overview (`web_search` failed with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `consecutive_count` in {2,3,4} x `ema_window` in {50,100} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.167 (12/72)
- `by_asset_class`: equity 12/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 0/24, high 0/24
- `best_cell` (low-vol-tercile artifact): SPY, consecutive_count=2,
  ema_window=50, Sharpe 2.49

## Full-sample sweep (QQQ / SPY)

| consecutive_count | ema_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 2 | 50  | 0.673 | 0.296 |
| 2 | 100 | 0.528 | 0.474 |
| 3 | 50  | 0.458 | 0.599 |
| 3 | 100 | 0.307 | **0.689** |
| 4 | 50  | 0.070 | 0.070 |
| 4 | 100 | 0.163 | 0.114 |

Best full-sample Sharpe across all 6 combos and both symbols is only
0.689 (SPY, consecutive_count=3, ema_window=100) — decisively below the
1.0 threshold, not a near-miss. Given the uniformly weak full-sample
Sharpe across every parameter combination, running the remaining
validator suite (MDD, TC-survival, walk-forward, parameter sensitivity)
would not change the outcome — skipped per Step 7 minimum-subset
guidance.

## Outcome

**Rejected** (decisive, not a near-miss — closest result 31% below
threshold). Crypto rejected decisively (0/36 grid cells).

## Notes

First Heikin Ashi (smoothed candle transform, distinct data
representation from every prior raw-OHLC-based indicator in this repo)
strategy tested. The color-flip exit is likely too eager (exits on any
single bearish HA candle, even a shallow pullback within a larger
uptrend), causing the strategy to repeatedly re-enter/exit and miss the
bulk of sustained trends — the sanity check showed 133 trades on QQQ at
consecutive_count=3/ema_window=100 alone over 7.7 years, a fairly high
turnover for a "trend-following" strategy. A future revisit could try a
looser exit (e.g. require 2 consecutive bearish HA candles, or an ATR
trailing stop as the source's full rule specifies) rather than a
same-bar single-candle flip exit.
