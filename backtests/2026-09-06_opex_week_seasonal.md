# OPEX Week Seasonal Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_opex_week_seasonal.py`
**Source:** https://www.quantifiedstrategies.com/options-expiration-week/ ("The Options Expiration Week Effect | OPEX Seasonality")

## Hypothesis

US equities exhibit above-average returns during the calendar week
containing the monthly options-expiration Friday (3rd Friday of the month),
attributed to dealer gamma-hedging / open-interest unwind dynamics into
expiration. Source's own simple test: buy at Monday open of OPEX week, sell
at Friday close — reported CAGR 2.8%, ~18% time invested, April strongest,
July/January weakest.

Operationalized here as: long from the Monday (or a later day, per
`entry_day_offset` param) of the week containing the 3rd Friday of each
month, through the close of that Friday (or through the rest of that week
if `exit_on_opex_friday=False`).

## Single-config validator results (default params: entry_day_offset=0, exit_on_opex_friday=True)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | 0.127 | 1.0 | FAIL | 0.228 | 0.25 | PASS |
| SPY | -0.229 | 1.0 | FAIL | 0.295 | 0.25 | FAIL |

Decisive Sharpe failure on both primary equity tickers at the source's own
default (Monday-entry) rule — the QuantifiedStrategies-reported ~2.8% CAGR
does not translate into an acceptable risk-adjusted return over this
2019-2026 window at the daily-bar granularity used here.

## Grid test summary

`param_grid={"entry_day_offset": [0, 2, 4], "exit_on_opex_friday": [True, False]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.056 (4/72 cells)**
- by_asset_class: equity 4/36 passed; crypto 0/36 passed (decisive reject for crypto)
- by_vol_regime: low 0/24, mid 4/24, high 0/24 — only the mid-vol tercile produced any passing cells
- best_cell: entry_day_offset=4 (i.e. only entering on OPEX Friday itself, essentially day-of, not the source's Monday-entry rule), exit_on_opex_friday=True, SPY, mid-vol regime, Sharpe 1.47
- worst_cell: entry_day_offset=2, SPY, high-vol regime, Sharpe -0.66

The one config that clears the bar (`entry_day_offset=4`) is a degenerate
variant that abandons the source's own core claim (buy the whole week from
Monday) and reduces to a single-day-of-expiration bet in one narrow vol
regime on one symbol — not a robust, broadly-supported finding.

## Decision: REJECTED

Both primary validators (Sharpe, and for SPY also max drawdown) fail
decisively at the source-recommended default parameterization on both
equity tickers tested; the grid's overall pass fraction (5.6%) confirms this
isn't a parameterization artifact — only a narrow, economically-different
variant (Friday-only entry) passes in one vol-regime/symbol combination.
Crypto is rejected outright (0/36, expected since OPEX is a US-listed-equity
options mechanism with no analog in the tested crypto pairs).

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(suggested_workload=max, but decisive full-sample + grid failure already
settles this — no ambiguity worth the extra compute).
