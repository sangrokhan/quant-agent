# Backtest Report: RSI(14) 45/75 Asymmetric Swing Mean Reversion — REJECTED

**Strategy file:** `strategies/2026-09-11_rsi14_asymmetric_swing.py`
**Hypothesis ID:** 2026-09-11-083

## Hypothesis

Per QuantifiedStrategies.com's "RSI 14 Debunked — Do This Instead" article
(https://www.quantifiedstrategies.com/rsi-14-debunked/, visited this
iteration), the source's own Amibroker optimization sweep (buy thresholds
{45,40,35,30,25} x sell thresholds {55,60,65,70,75} on standard 14-day
RSI, S&P 500 since 1993) found the single best CAGR combo to be: buy when
RSI(14) < 45, sell when RSI(14) > 75. The source's own finding is
explicitly negative — this best-of-25 combo still underperforms
buy-and-hold on CAGR (8.51% vs 10.1%) with an IDENTICAL max drawdown
(55%). We tested whether this repo's own vectorbt-backed validator suite
(Sharpe/MDD/TC-survival/walk-forward/param-sensitivity — a different lens
than the source's own CAGR/MDD-only reporting) might still find risk-adjusted
value despite the source's own pessimistic framing, using a slightly wider
grid (buy∈{40,45,50}, sell∈{65,75}) that includes the source's disclosed
best combo.

## Single-config validator results (QQQ, buy_threshold=50.0, sell_threshold=75.0; 2016-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ (narrow) | 1.006 | ≥ 1.0 |
| Max drawdown | ❌ **decisive fail** | 0.355 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 31 trades) | ✅ | net Sharpe 0.988 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | ✅ | 4/4 splits positive | ≥ 0.75 pass fraction |
| Parameter sensitivity (6-combo grid: buy∈{40,45,50} × sell∈{65,75}) | ✅ | relative_std 0.166 | ≤ 0.5 |

**Decision: REJECTED** — MDD (0.355) is 42% over the 0.25 threshold on the
single best-performing config found in the grid; this asymmetric-threshold
buy-and-hold-like RSI rule spends most of its time long (position value_counts
showed ~81% time-in-market on SPY) and inherits nearly all of the
underlying asset's own drawdown risk, consistent with the source's own
observation that this config's drawdown matched buy-and-hold's (55% on
their full-history S&P 500 backtest).

## Step 6 grid summary (param_grid buy_threshold=[40,45,50] x sell_threshold=[65,75], symbols equity=[SPY,QQQ] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2016-01-01 to 2026-09-01)

- total_cells=72, passed=18, **pass_fraction=0.25**
- by_asset_class: equity 18/36 pass, crypto **0/36 decisive reject**
- by_vol_regime: low 8/24, mid 10/24, **high 0/24 decisive fail**
- best_cell: QQQ, buy=50, sell=75, low-vol, Sharpe 2.07
- worst_cell: BTC/USDT, buy=40, sell=65, mid-vol, Sharpe -0.06
- Sharpe-only grid pass_fraction (25%) masks the fact that even the
  passing cells' underlying full-sample MDD is still decisive-fail —
  `run_strategy_grid`'s per-cell pass/fail is Sharpe+MDD on the SLICED
  vol-regime subsample, not the full-sample MDD used in the Step 7
  single-config validator, which is why grid "passes" don't guarantee the
  full-sample MDD check also passes.

## Notes

- Source: https://www.quantifiedstrategies.com/rsi-14-debunked/ (visited
  this iteration, first read of this URL). Source's own negative framing
  (own best combo still underperforms buy-and-hold with identical
  drawdown) is directly confirmed and extended by this repo's own
  validator suite: the config clears Sharpe/TC/WF/param-sensitivity
  narrowly but fails MDD decisively, consistent with a strategy that is
  functionally "buy-and-hold with occasional cash pauses" rather than a
  genuine risk-reducing timing edge.
- Novel construction for this repo: standard RSI(14) (not RSI2/composite),
  wide asymmetric 45-50/75 threshold band (not symmetric 30/70), no trend
  filter — distinct from 2026-09-03-005 (RSI2+SMA200) and
  2026-09-04-077 (RSI centerline-cross momentum).
- Future revisit idea (not pursued this iteration): layer a 200-SMA trend
  filter or volatility-regime gate onto this same RSI(14) 45/75 rule to
  see if the MDD failure can be fixed without destroying the Sharpe edge —
  several prior strategies in this repo (e.g. 2026-09-03-005) show this
  pattern (raw RSI rule fails MDD, trend-filtered version passes).
