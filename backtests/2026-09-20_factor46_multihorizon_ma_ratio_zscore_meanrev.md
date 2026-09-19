# Factor46 Multi-Horizon MA-Ratio Mean Reversion (time-series z-score adaptation)

**Hypothesis:** Per Quantitativo's "Modern Statistical Arbitrage"
(https://www.quantitativo.com/p/modern-statistical-arbitrage), a paper
testing 190+ cross-sectional equity factors identifies "Factor 46",
`(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/(4*CLOSE)`,
as a strong short-horizon mean-reversion signal (source's own cross-
sectional single-factor Sharpe 0.53-1.46 across six equity universes,
though the source itself notes a single factor alone is not tradeable and
needs combining with 16 others). Adapted here to a single-asset time-series
z-score (this repo's loaders are single-symbol, no cross-sectional
universe available): long when the asset's own factor46 value is
`entry_z` std devs above its own trailing rolling mean (unusually far
below its own multi-horizon blended average), exit on reversion to
`exit_z` or a `max_hold_days` time-stop.

## Strategy file
`strategies/2026-09-20_factor46_multihorizon_ma_ratio_zscore_meanrev.py`

## Grid test summary (entry_z in {1.0,1.5,2.0} x max_hold_days in {5,10}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026)

- pass_fraction: 0.181 (13/72 cells)
- by_asset_class: equity 13/36, crypto 0/36 (decisive crypto reject)
- by_vol_regime: low 9/24, mid 4/24, high 0/24 -- edge (where present at all) concentrated entirely in low-vol regime slices, consistent with this being a short-horizon mean-reversion signal that only fires cleanly in calm markets.

## Single-config validators (full sample 2015-2026)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Trades |
|---|---|---|---|---|---|
| QQQ | entry_z=1.0, hold=10 | 0.757 FAIL | 0.210 PASS | 0.656 PASS | 118 |
| QQQ | entry_z=1.0, hold=5 | 0.653 FAIL | 0.245 PASS | 0.523 PASS | 147 |
| QQQ | entry_z=1.5, hold=10 | 0.525 FAIL | 0.275 FAIL | 0.462 FAIL | 76 |
| QQQ | entry_z=2.0, hold=10 | 0.358 FAIL | 0.242 PASS | 0.320 FAIL | 42 |
| SPY | entry_z=1.0, hold=10 | 0.541 FAIL | 0.343 FAIL | 0.442 FAIL | 105 |
| SPY | entry_z=1.0, hold=5 | 0.579 FAIL | 0.318 FAIL | 0.443 FAIL | 134 |
| SPY | entry_z=1.5, hold=10 | 0.430 FAIL | 0.343 FAIL | 0.360 FAIL | 72 |
| SPY | entry_z=2.0, hold=10 | 0.267 FAIL | 0.343 FAIL | 0.224 FAIL | 43 |

Best full-sample config (QQQ, entry_z=1.0/hold=10) still fails Sharpe
decisively (0.757 vs 1.0 threshold). SPY fails both Sharpe and MDD at
every config tried. No full-sample config clears the Sharpe bar despite
the grid's apparently-OK-looking low-vol pass_fraction -- the low-vol-only
edge does not survive being averaged across the full sample (which
includes mid/high-vol periods where the signal loses money), consistent
with the source's own finding that a single unblended factor is
"encouraging, but on its own not a finished strategy" and only works after
combining 17 signals cross-sectionally into a diversified portfolio (not
replicable here with a single-symbol time-series adaptation).

## Outcome

**Rejected.** Confirms the source's own caveat: a lone cross-sectional
factor, especially adapted through-time on a single symbol rather than
combined cross-sectionally as the source's own methodology requires, does
not clear this repo's Sharpe threshold. Not a feasibility dead-end for the
whole "combine many factors" idea, but the true test (a cross-sectional
multi-factor portfolio) is infeasible with this repo's single-symbol
data/loaders.py.
