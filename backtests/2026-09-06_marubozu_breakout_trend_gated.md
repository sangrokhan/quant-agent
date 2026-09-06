# Bullish Marubozu Breakout, Trend-Gated, Long-Only

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_marubozu_breakout_trend_gated.py`
**Knowledge base id:** 2026-09-06-146

## Hypothesis

Per Trading Setups Review's Marubozu Candlestick Pattern Trading Guide
(https://www.tradingsetupsreview.com/marubozu-candlestick-pattern-trading-guide/),
a Marubozu candle (body >= 95% of range) represents "urgency of market
players... when we see a bullish Marubozu, we expect prices to continue
rising in the short-term." Combined with the Google-search-surfaced
TrendSpider breakout tactic ("Enter when the price breaks above a bullish
Marubozu high"), tested as: a bullish Marubozu forming within a confirmed
uptrend (close>SMA(200)) marks a high-conviction bar; entry on the
subsequent break above that bar's high (within an expiry window); exit on a
failure back below the Marubozu's low, trend break, or time-stop. First
candlestick-pattern strategy in this repo using a body-to-range-ratio
definition.

## Grid test (Step 6)

144 cells: `marubozu_body_pct` in [0.90,0.95] x `breakout_expiry_bars` in
[3,5,10] x `max_hold_days` in [10,20] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3
vol terciles.

- **Overall pass_fraction:** 0.118 (17/144)
- **by_asset_class:** equity 17/72 (0.236); crypto 0/72 (decisive reject)
- **by_vol_regime:** low 17/48 (0.354); mid 0/48 (decisive); high 0/48
  (decisive)
- **Best cell:** marubozu_body_pct=0.90/breakout_expiry_bars=10/max_hold_days=20,
  QQQ, low-vol regime, Sharpe=2.76

## Single-config validators (best-cell config, QQQ full sample, 20 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.880 | 1.0 | **FAIL (near-miss)** |
| Max drawdown | 0.121 | 0.25 | pass |
| Transaction cost survival | 0.830 | 0.5 | pass |

Walk-forward/parameter-sensitivity skipped given the low-vol-only decisive
regime pattern (mid/high vol both 0/48) makes a full pass unlikely, per
RESEARCH_LOOP.md Step 7 workload-scoping guidance.

## Decision: REJECTED

Sharpe (0.880) narrowly misses the 1.0 threshold on full-sample QQQ; MDD and
transaction-cost survival both pass comfortably. Crypto and mid/high vol
regimes are decisively rejected (0/96 combined cells), so this is a
low-vol-equity-only setup with a low trade count (20 trades over 7.7yr) --
similar low-signal-frequency caveat as other rare-pattern strategies in this
repo (e.g. A/D Line bullish divergence, 2026-09-06-138). Could be revisited
with a looser trend/body-ratio threshold to raise trade frequency without
losing the demonstrated low-vol edge.
