# N-Day Pullback Reversal with 200-day trend filter + inverse-vol sizing

**Hypothesis:** Per Quantpedia's "Testing an AI-Assisted Research Workflow
for Multi-Asset Pullback Strategy Discovery"
(https://quantpedia.com/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/,
via https://www.advancedinvesting.org mirror, browser_exec fallback):
200-day MA trend filter + N-consecutive-down-days pullback trigger +
short fixed hold + volatility-adjusted sizing across six liquid ETFs
2006-2025. Source's own best spec (200d MA, 2-day pullback, 1-day hold):
Sharpe ~0.95. Conservative 3-day pullback variant: similar return to
buy-and-hold, 2.4x smaller drawdown.

## Strategy file
`strategies/2026-09-20_ndown_pullback_reversal_voltarget.py`

## Grid test summary (pullback_days in {2,3} x hold_days in {1,3,5}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026)

- pass_fraction: 0.153 (11/72 cells)
- by_asset_class: equity 10/36, crypto 1/36 (near-total crypto reject)
- by_vol_regime: low 7/24, mid 3/24, high 1/24
- best_cell: SPY, pullback_days=3/hold_days=5, low-vol regime, Sharpe 1.89

## Single-config validators (SPY, pullback_days=3, hold_days=5, full sample 2015-2026)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.006 | >= 1.0 | PASS (razor-thin) |
| Max drawdown | 0.062 | <= 0.25 | PASS |
| TC survival (10bps/trade, 89 trades) | net Sharpe 0.738 | >= 0.5 | PASS |
| Walk-forward (4 manual splits) | 4/4 splits positive Sharpe (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (pullback_days in {2,3,4} x hold_days in {3,5,7}) | rel_std 0.656 | <= 0.5 | **FAIL** |

Parameter sensitivity fails: while pullback_days=2/3 with hold_days=5/7
all cluster around Sharpe 0.85-1.01, pullback_days=4 collapses to
near-zero or negative Sharpe (0.235, 0.059, -0.046) -- the strategy's
edge is fragile to a seemingly small change in the pullback-day count,
consistent with the source's own finding that "the mean-reversion edge is
concentrated almost entirely in the first day after entry" (a signature
of a fragile, easily-diluted short-horizon effect rather than a robust
one).

QQQ fails decisively at every config tried (best full-sample Sharpe 0.399,
most configs near-zero or negative) -- this pullback mechanism does not
transfer to QQQ's higher-beta profile the way it does to SPY.

## Outcome

**Rejected** (near-miss on Sharpe, decisive fail on parameter sensitivity).
SPY's best config passes 4/5 validators but the parameter-sensitivity
failure means the specific pullback_days=3 choice is not a robust,
generalizable setting -- a small change (to 4 days) destroys the edge.
QQQ and crypto reject decisively. Consistent with source's own observation
that the edge concentrates in the very first post-entry day, which makes
this a fragile short-horizon effect prone to exactly this kind of
parameter fragility once implemented mechanically.
