# Hammer Reversal, Downtrend-Gated, Long-Only

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_hammer_reversal_downtrend_gated.py`
**Knowledge base id:** 2026-09-06-147

## Hypothesis

Per TradingView's "Candlestick Patterns" script description
(https://www.tradingview.com/scripts/hammer/) and a Google-search-surfaced
strategy snippet ("The strategy goes long on the next bar open when a
hammer is detected, with a stop loss at the low of the hammer bar and a
target at the high"): a Hammer candle (small body, lower wick >=
wick_to_body_ratio x body, minimal upper wick) appearing after a downtrend
(close < SMA(trend_window)) marks a bullish reversal; long entry on the
subsequent bar, stop at the Hammer's low, target at Hammer's high plus a
multiple of its range. First Hammer-pattern strategy in this repo.

## Grid test (Step 6)

216 cells: `wick_to_body_ratio` in [1.5,2.0,2.5] x `trend_window` in
[20,50] x `max_hold_days` in [10,15,20] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3
vol terciles.

- **Overall pass_fraction:** 0.088 (19/216)
- **by_asset_class:** equity 19/108 (0.176); crypto 0/108 (decisive reject)
- **by_vol_regime:** low 0/72 (decisive reject); mid 9/72 (0.125); high
  10/72 (0.139) -- unusual REVERSE pattern vs most prior strategies in this
  repo (which typically only work in low-vol; this one has zero low-vol
  passes but some mid/high-vol passes, consistent with a reversal pattern
  needing genuine volatility/panic to be meaningful)
- **Best cell:** wick_to_body_ratio=2.0/trend_window=50/max_hold_days=10,
  QQQ, mid-vol regime, Sharpe=1.64

## Single-config validators (best-cell config, QQQ full sample, 15 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.407 | 1.0 | **FAIL** |
| Max drawdown | 0.092 | 0.25 | pass |
| Transaction cost survival | 0.354 | 0.5 | **FAIL** |

## Decision: REJECTED

The grid's best cell (isolated mid-vol slice, Sharpe 1.64) does not survive
full-sample confirmation: Sharpe collapses to 0.407 and transaction-cost
survival fails (net Sharpe 0.354 after 10bps/trade x 15 trades) -- a classic
narrow-slice cherry-pick, the same recurring pattern seen throughout this
repo. Very low trade count (15 over 7.7yr) limits statistical confidence
regardless. Crypto and low-vol regime are decisively rejected. The
mid/high-vol-only pass pattern (novel vs this repo's usual low-vol skew) is
worth noting for a future loop, but this specific config does not clear the
bar.
