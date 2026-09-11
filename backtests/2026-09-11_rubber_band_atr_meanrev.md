# 2026-09-11 Rubber Band ATR-Band Mean Reversion — Backtest Report

**Hypothesis:** ATR-band mean reversion below rolling N-day high: long when
close < (rolling high_window-day High − band_mult × rolling range_window-day
average True Range); exit when close crosses back above yesterday's high.
Source: https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(visited this iteration; the Substack article with the same name has the
same rule but is paywalled behind a subscription). Source's own disclosed
default (range_window=5, high_window=5, band_mult=2.5) on SPY: average
gain per trade 0.66%, win rate 77%, annual return 6.4% at 14% time
invested.

## Single-config validators (source's default config: range_window=5,
high_window=5, band_mult=2.5, SPY/QQQ, 2010-01-01 to 2024-01-01)

| Symbol | Sharpe | MDD | Passed |
|---|---|---|---|
| SPY | 0.651 | 0.142 | Sharpe FAIL |
| QQQ | 0.671 | 0.157 | Sharpe FAIL |

## Fine-tune sweep (range_window in {3,4,5,7} x high_window in {3,5,7,8,9,10} x band_mult in {1.5,...,3.0})

Best full-sample config found: **QQQ, range_window=3, high_window=7,
band_mult=2.0** — Sharpe 1.387 ✅, MDD 0.131 ✅, walk-forward (manual
4-way range-split; `check_walk_forward` raises on installed vectorbt
1.1.0, pre-existing bug flagged in 2026-09-10-021/022) 4/4 splits positive
(1.0) ✅ — **but transaction-cost survival decisively fails**: net Sharpe
0.451 at repo-standard 10bps/trade (788 trades over 14yr) vs 0.5
threshold. SPY at the same config: Sharpe 0.805 (fail).

A broader sweep across ~20 nearby configs (see below) found net-Sharpe-
after-10bps topping out around 0.45, never clearing 0.5 -- this is an
inherently high-turnover mean-reversion construction (roughly 55-90
trades/year at the tuned configs) where the tuning that improves raw
Sharpe (tighter bands, more trades) directly increases the cost drag,
and configs with fewer trades (wider bands) have lower raw Sharpe to
begin with -- no config threads the needle.

| range_window | high_window | band_mult | Sharpe | MDD | trades | net-Sharpe-10bps |
|---|---|---|---|---|---|---|
| 3 | 7 | 2.0 | 1.387 | 0.131 | 788 | 0.451 |
| 3 | 9 | 2.0 | 1.234 | 0.150 | 885 | 0.342 |
| 3 | 10 | 2.25 | 1.248 | 0.159 | 767 | 0.409 |
| 4 | 7 | 2.25 | 1.131 | 0.117 | 654 | 0.378 |
| 3 | 7 | 2.5 | 1.054 | 0.117 | 492 | 0.421 |

## Step 6 grid summary (band_mult in [2.0,2.5,3.0] x trend_gate in [False,True], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3, default range_window/high_window=5/5)

- 72 total cells, 14 passed (pass_fraction 0.194)
- **by_asset_class**: equity 14/36 (38.9%), crypto 0/36 (0%)
- **by_vol_regime**: low 10/24, mid 4/24, high 0/24
- Best cell: QQQ, band_mult=2.0/trend_gate=False, low-vol regime, Sharpe 2.11
- Worst cell: ETH/USDT, band_mult=3.0/trend_gate=False, mid-vol regime, Sharpe -0.44

The 200/50-SMA trend_gate (mirroring the Substack teaser's QQQ variant)
consistently REDUCES trade count and Sharpe versus the ungated version in
every config tested -- the source's trend filter appears optimized for a
different (likely tighter/different-period) band configuration than what
this repo could confirm from the fully-disclosed rule, so it was not
carried into the final fine-tuned config.

## Decision: REJECTED

Source's own default config fails Sharpe on both SPY/QQQ. A fine-tuned
config (range_window=3, high_window=7, band_mult=2.0) rescues Sharpe/MDD/
walk-forward on QQQ but decisively fails transaction-cost survival (net
Sharpe 0.451 vs 0.5 at repo-standard 10bps/trade) — this mean-reversion
construction's edge is concentrated in ~55-90 trades/year, too frequent
to survive typical retail-equivalent trading costs at this repo's cost
assumption. SPY never clears Sharpe at any config tested. Crypto rejected
decisively (0/36).

## Notes for future iterations

- Near-miss specifically on transaction costs (0.451 vs 0.5), not on
  Sharpe/MDD/walk-forward, similar in character to the same-cron-trigger
  cross-asset stress reversal (2026-09-11-072) -- both are high-turnover
  mean-reversion constructions. A pattern is emerging this cron trigger:
  short-hold mean-reversion ideas keep clearing Sharpe/MDD but failing
  transaction-cost survival at the repo's 10bps/trade standard. Future
  iterations chasing this family should specifically search for LOWER-
  turnover mean-reversion variants (e.g. requiring the band to be crossed
  for N consecutive days before entry, or widening the exit trigger) to
  reduce trade frequency without proportionally losing edge.
- The Substack teaser's trend-gated 200/50-SMA QQQ variant (CAGR 14.6%,
  MDD 27%) could not be reproduced from the fully-disclosed rule found
  this iteration -- its exact band parameters were paywalled. If a future
  iteration can access the Substack subscriber content, revisit with the
  source's own exact parameters rather than this repo's independent
  fine-tune.
