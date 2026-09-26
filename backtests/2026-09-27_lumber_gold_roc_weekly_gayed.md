# Backtest Report: Lumber/Gold Weekly Gayed RORO (2026-09-27)

## Hypothesis

Per https://allocatesmartly.com/the-lumber-gold-strategy/ (Michael Gayed's
"Risk On / Risk Off" indicator, found via Google AI-overview synthesis,
`browser_exec` since `web_search` DDGS backend erroring this session):
weekly, at Friday's close, compare lumber's (WOOD ETF proxy) 13-week (~65
trading day) return to gold's (GLD) 13-week return. Lumber outperforming ->
risk-on (long equities); gold outperforming -> risk-off (source uses
cash/T-bills, here flat, per this repo's single-price_df contract, same
simplification as the already-rejected prior attempt).

Distinct from this repo's already-rejected 2026-09-05-059 (which used the
Lumber/Gold RATIO's own momentum, daily-rebalanced) via the source's
actual disclosed mechanic: two SEPARATE ROC series compared directly, and
locked weekly rather than reacting daily.

## Grid test summary (Step 6)

param_grid: roc_window=[45,65,85]; symbols: equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3 (2018-01-01 to 2026-09-01).

- total_cells: 36, passed_cells: 6, **pass_fraction: 0.167**
- by_asset_class: equity 5/18, crypto 1/18
- by_vol_regime: low 6/12 (50%), mid 0/12, high 0/12 -- only survives in
  low-vol regime
- best_cell: ETH/USDT mid-vol roc_window=85, Sharpe=2.05 (crypto anomaly,
  likely a thin/noisy cell given crypto's low overall pass rate)
- worst_cell: QQQ high-vol roc_window=45, Sharpe=-0.48

## Single-config validators (Step 7) -- QQQ and SPY, full sample

| roc_window | Symbol | Sharpe | MDD | TC-survival | Trades |
|---|---|---|---|---|---|
| 65 | QQQ | 0.409 FAIL | 0.342 FAIL | 0.376 FAIL | 27 |
| 85 | QQQ | 0.383 FAIL | 0.253 FAIL | 0.348 FAIL | 28 |
| 65 | SPY | 0.460 FAIL | 0.296 FAIL | 0.411 FAIL | 27 |
| **85** | **SPY** | **0.620 FAIL** | **0.184 PASS** | **0.565 PASS** | 28 |

No config clears Sharpe on either symbol; SPY at roc_window=85 comes
closest (2/3 validators pass) but the core Sharpe requirement fails
decisively across the board (0.38-0.62 vs 1.0 threshold). Consistent with
the grid's low 16.7% pass fraction and the strategy holding up only in a
narrow low-vol tercile slice.

## Verdict: REJECTED

Fails full-sample Sharpe on both tested equity symbols regardless of
roc_window; crypto shows no consistent edge (1/18 grid cells, likely
noise). This exact Gayed weekly two-series-ROC-comparison construction
does not fare meaningfully better than the repo's prior ratio-momentum
variant (2026-09-05-059, also rejected) -- the flat-when-risk-off
simplification (missing the source's own TLT/bond defensive leg) likely
continues to understate the original strategy's real performance, as noted
in the prior entry. Strategy file kept in `strategies/` as a rejected
record.
