# Bollinger Bandwidth-percentile squeeze breakout (no Keltner)

**Hypothesis:** Per quantifiedstrategies.com's Bollinger Band Squeeze
article, Bollinger Bandwidth (BW = (upper-lower)/basis) contracting to a
rolling N-day low identifies a volatility-compression "squeeze" that often
precedes a breakout. Operationalized as: squeeze state = BW at/below its
own trailing `bw_lookback`-day `squeeze_percentile` quantile; entry = a
squeeze within the last `squeeze_recency` bars AND close breaks above the
upper Bollinger Band, gated by close > SMA(trend_window); exit on close
crossing below the basis SMA or a max_hold_days time-stop.

Source: https://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/
(bandwidth-percentile-squeeze concept disclosed free; source's own numeric
backtest rule paywalled, and their own PEP example underperformed
buy-and-hold, 12.5% vs 14.8%).

Novelty: distinct from prior Keltner-Channel-based squeeze strategies in
this repo (TTM Squeeze id=2026-09-04-091, LazyBear Squeeze Momentum
id=2026-09-04-126) -- pure Bollinger Bandwidth percentile-rank squeeze
detector, no Keltner Channel comparison.

**Note:** this iteration also verifies the ccxt provider tz-aware Timestamp
bug fix committed earlier this run (9f5a7db) -- crypto grid cells now
execute (0/48 passed on genuine strategy performance, not a data-load
error as in the prior 3 iterations this run).

## Step 6 — Grid summary

Grid: `squeeze_percentile in {0.15,0.25}`, `squeeze_recency in {3,7}`,
`max_hold_days in {15,25}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 96 total cells.

- pass_fraction: 0.208 (20/96)
- by_asset_class: equity 20/48 passed; crypto 0/48 (genuine strategy
  underperformance this time, confirmed data loaded successfully)
- by_vol_regime: low 12/32, mid 0/32, high 8/32
- best_cell: squeeze_percentile=0.15, squeeze_recency=3, max_hold_days=25,
  QQQ, low-vol, Sharpe 1.73

## Step 7 — Single-config validation (squeeze_percentile=0.15, squeeze_recency=3, max_hold_days=25)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | -0.183 FAIL | 0.946 FAIL (marginal) |
| Max drawdown (<=0.25) | 0.152 PASS | 0.028 PASS |
| Net-of-cost Sharpe (>=0.5, 10bps/trade) | -0.201 FAIL | 0.914 PASS |
| Param sensitivity relative_std (<=0.5) | 0.049 PASS | 0.134 PASS |
| num_trades | 4 | 4 |
| Walk-forward | not run — same vectorbt limitation as prior entries this run. |

## Step 8 — Decision

**Rejected.** Both symbols produce only 4 trades over 7.7yr at the
grid-best config — far too thin a sample for the headline metrics to be
statistically meaningful, and even so QQQ's full-sample Sharpe is negative.
SPY's Sharpe (0.946) is close to but still below the 1.0 threshold on the
same thin sample. The squeeze condition is simply too rare a setup at this
percentile/recency combination on daily equity bars to produce a
usable trade count; a future loop could revisit with a much looser
squeeze_percentile or shorter bw_lookback to generate more signals before
re-testing. Crypto rejected on 0/48 grid cells (genuine underperformance,
confirmed the ccxt data-load bug fix from earlier this run is working).
