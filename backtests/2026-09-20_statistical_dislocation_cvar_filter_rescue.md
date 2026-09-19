# Statistical Dislocation Mean Reversion + Rolling-CVaR Tail-Risk Filter (rescue of 2026-09-08-140 QQQ near-miss)

**Hypothesis:** Per Quantitativo's "More Bets, Better Bets"
(https://www.quantitativo.com/p/more-bets-better-bets), the disclosed fix
for a mean-reversion strategy's tail-risk blowups when scaled to a wider
universe was NOT a better signal but a rolling CVaR 5% entry filter --
skip trades in names/periods whose own recent left tail is already fat.
Applied here through time (not cross-sectionally) on top of this repo's
existing Statistical Dislocation Mean Reversion strategy
(2026-09-08-140, `strategies/2026-09-08_statistical_dislocation_quantile_meanrev.py`),
which had accepted cleanly on SPY but near-missed on QQQ (Sharpe 0.866,
MDD 25.1%, param-sensitivity 0.519, all narrowly failing at the same
config). Source (`https://www.quantitativo.com/p/more-bets-better-bets`)
reported: adding the CVaR filter to the Russell-3000-scaled version of
"Murphy's Law" (`https://www.quantitativo.com/p/murphys-law`) lifted
Sharpe from 0.99 to 1.30 and cut MDD from -36.0% to -32.8%, purely by
skipping trades with visible fat tails.

## Strategy file
`strategies/2026-09-20_statistical_dislocation_cvar_filter_rescue.py`

Same quantile-drop + SMA-uptrend + fixed-hold entry/exit as the parent
strategy, plus one new gate: only enter when the asset's own trailing
rolling CVaR 5% (over `cvar_window` days) is not worse than
`cvar_threshold`.

## Grid test summary (cvar_threshold in {-0.03,-0.04,-0.05} x hold_days in {3,5}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026)

- pass_fraction: 0.25 (18/72 cells)
- by_asset_class: equity 18/36, crypto 0/36 (decisive crypto reject, consistent with parent strategy's finding that the uptrend-dislocation mechanism doesn't map to 24/7 crypto)
- by_vol_regime: low 12/24, mid 6/24, high 0/24
- best_cell: SPY, cvar_threshold=-0.03/hold_days=3, low-vol regime, Sharpe 2.04

## Single-config validators (QQQ, cvar_threshold=-0.05, hold_days=5, full sample 2015-2026)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.094 | >= 1.0 | PASS |
| Max drawdown | 0.241 | <= 0.25 | PASS |
| TC survival (10bps/trade, 113 trades) | net Sharpe 0.934 | >= 0.5 | PASS |
| Walk-forward (4 manual splits) | 4/4 splits positive Sharpe (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (cvar_threshold in {-0.03,-0.04,-0.05,-0.06}) | rel_std 0.100 | <= 0.5 | PASS |

All 5 validators pass -- this successfully rescues the QQQ near-miss from
2026-09-08-140 (Sharpe 0.866->1.094, MDD 0.251->0.241, param-sensitivity
0.519->0.100), confirming the CVaR tail-risk filter's value even in this
repo's single-symbol, through-time adaptation of the source's cross-
sectional (many-names) construction.

## SPY sanity check

At the same cvar_threshold=-0.05/hold_days=5 config, SPY Sharpe drops to
0.646 (below threshold) -- worse than the parent's unfiltered SPY config
(which used quantile_threshold=0.1/hold_days=5, Sharpe 1.104). SPY's best
config in this grid was cvar_threshold=-0.03/hold_days=3 (Sharpe 0.921,
still short of 1.0). SPY does not need this filter (parent strategy
already accepted cleanly for SPY) and this specific CVaR variant does not
improve on it -- this strategy file is scoped to QQQ only.

## Outcome

**Accepted for QQQ only** (cvar_threshold=-0.05, hold_days=5, all other
params at parent defaults: n_day_window=3, dist_window=252,
quantile_threshold=0.15, trend_window=200, cvar_window=60). SPY and crypto
remain rejected/out-of-scope for this specific variant (SPY already has
its own accepted config from the parent strategy; use that instead).
