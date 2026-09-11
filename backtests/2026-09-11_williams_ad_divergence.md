# Williams Accumulation/Distribution (WAD) Bullish Divergence — Backtest Report (2026-09-11)

## Hypothesis
Per QuantifiedStrategies.com's article on the Williams A/D indicator
(https://www.quantifiedstrategies.com/williams-accumulation-distribution/),
quoting Larry Williams' own 1995 Las Vegas seminar verbatim: cumulative
non-volume accumulation/distribution index; "I look for divergence
between price and the A/D. If the price is up and not matched by A/D, a
sell is coming. If the price breaks to a new low and A/D does not, then a
buy is coming." Implemented as: long entry when price makes a new
N-bar low while WAD does not confirm (bullish divergence); exit on
bearish divergence (price new N-bar high, WAD doesn't confirm) or a
max_hold_days time-stop. First WAD strategy in this repo, distinct from
the volume-weighted Chaikin A/D Line already tested.

## Grid test (Step 6)
`param_grid`: divergence_window [10,20,30] x max_hold_days [10,15,25];
symbols equity [QQQ, SPY] + crypto [BTC/USDT, ETH/USDT]; vol_regime_splits=3.
108 total cells.

- **pass_fraction: 0.111** (12/108)
- by_asset_class: equity 12/54 passed; **crypto 0/54** (decisive reject)
- by_vol_regime: low 8/36; mid 1/36; high 3/36
- best_cell: SPY, divergence_window=30/max_hold_days=25, low-vol regime,
  Sharpe 1.80

## Single-config validation (Step 7) — best config: divergence_window=30,
max_hold_days=25, 2019-2026

| Metric | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.427 **FAIL** | 1.054 pass | >= 1.0 |
| Max Drawdown | 0.202 pass | 0.249 pass | <= 0.25 |
| Net Sharpe after 10bps/trade costs | 0.408 **FAIL** | 1.030 pass | >= 0.5 |
| Walk-forward pass fraction | 1.0 (4/4) pass | 1.0 (4/4) pass | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.857 **FAIL** | 0.692 **FAIL** | <= 0.5 |
| Trades | 10 | 14 | — |

## Decision: REJECT
SPY fails Sharpe, TC-survival, and parameter sensitivity decisively. QQQ
passes Sharpe/MDD/TC/walk-forward at the grid-best config but fails
parameter sensitivity badly (rel. std 0.692 vs 0.5 threshold) -- with
only 14 total trades over 8 years, the grid-best config is a fragile
single lucky point rather than a robust plateau (relative std nearly
0.7-0.86 across both symbols confirms the signal is highly sensitive to
the exact divergence_window/max_hold_days chosen). Crypto rejected
decisively (0/54). The precise, well-disclosed signal logic (unusual for
this site -- most articles paywall the exact rule) does correctly
identify a real but very low-frequency divergence pattern; the low trade
count (10-14 over 8 years) makes every metric statistically thin and
unreliable at any single parameter setting.
