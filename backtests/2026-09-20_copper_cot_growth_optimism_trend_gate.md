# CFTC COT Copper Growth-Optimism Trend Gate — Backtest Report

**Hypothesis:** Copper ("Dr. Copper") Managed Money net position SIGN
(positive = "growth optimism" per CME Group's own framing) confirms a
copper price uptrend. Trend-confirmation gate: long CPER only when close
> SMA(50) AND Copper Managed Money net position is positive. Eighth COT
strategy this cron trigger, eighth market (Copper futures — first use of
Copper COT data in this repo).

**Sources:**
- https://www.google.com/search?q=copper+futures+COT+managed+money+net+position+leading+indicator+economic+trading+rule (browser_exec Google SERP; CME Group's own "Copper: A Leading Indicator for Growth" whitepaper, MacroMicro, StoneX)
- https://publicreporting.cftc.gov/resource/72hh-3qpy.json (`COPPER- #1 - COMMODITY EXCHANGE INC.` market, only 241 weekly rows available from 2022-02 — same short-history limitation as the E-mini S&P 500 market tried in -041)

**Data:** CPER/SPY daily OHLCV via `load_equity` (restricted to 2022-03+ per COT data availability); BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {trend_window: [30,50,80]}` (single param, smaller grid per
`suggested_workload` budget management this iteration), `symbols =
{equity: [CPER,SPY], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 36, passed_cells: 7, **pass_fraction: 0.194**
- by_asset_class: equity 7/18 passed (39%, but concentrated on SPY not CPER — the intended primary asset), crypto 0/18 passed
- by_vol_regime: low 3/12, mid 3/12, high 1/12
- best_cell: trend_window=50, SPY, low-vol, Sharpe 2.07 (SPY, not the intended primary market)
- worst_cell: trend_window=50, CPER, high-vol, Sharpe -1.07

## Primary-config validation (CPER, trend_window=50 — the intended primary asset)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period, 2022-03 to 2026-09) | 0.173 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.278 | ≤ 0.25 | **FAIL** |

## Decision: REJECTED

The intended primary asset (Copper/CPER) fails decisively on both Sharpe
and max drawdown. The grid's "passes" concentrated on SPY, which is not a
genuine leg of this hypothesis (copper COT positioning was never expected
to be a growth-confirmation signal for SPY specifically over CPER itself)
— a spurious pass, not evidence of a real edge. The short 241-week COT
history for this specific Copper market classification (same limitation
noted in -041 E-mini S&P) likely also constrains statistical power.
Strategy file and this report kept as a record of a rejected attempt.
