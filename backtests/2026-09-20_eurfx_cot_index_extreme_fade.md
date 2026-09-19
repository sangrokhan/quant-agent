# CFTC COT Euro FX "COT Index" (1-Year Min-Max) Extreme Fade — Backtest Report

**Hypothesis:** The widely-used "COT Index" (1-year min-max normalization
of net position, 0-100 scale, distinct from the percentile-rank
normalization used in this cron trigger's earlier COT strategies) applied
to Euro FX futures leveraged-money net position: go long EUR/USD (FXE)
when the COT Index is <= 20 (speculators near-least-bullish of the past
year), flat otherwise. Seventh COT strategy this cron trigger, seventh
market (Euro FX futures — first currency-futures COT data used in this
repo) and first use of the min-max "COT Index" normalization technique
(vs. percentile-rank used in -037/-039/-041/-042).

**Sources:**
- https://www.google.com/search?q=Euro+FX+COT+non-commercial+extreme+net+position+contrarian+forex+trading+rule (browser_exec Google SERP; FXNX.com "When the COT Index for Non-Commercials hits 90% or higher..."; CME Group's own FX-COT article)
- https://publicreporting.cftc.gov/resource/gpe5-46if.json (`EURO FX - CHICAGO MERCANTILE EXCHANGE` market, 1058 weekly rows since 2006)

**Data:** FXE/UUP daily OHLCV via `load_equity`; BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {window_weeks: [26,52,78], low_idx: [10.0,20.0,30.0]}`,
`symbols = {equity: [FXE,UUP], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 13, **pass_fraction: 0.120**
- by_asset_class: **equity 2/54 passed** (the intended asset class — decisive fail), crypto 11/54 passed (spurious — Euro FX COT signal has no economic link to crypto)
- by_vol_regime: low 11/36, mid 2/36, high 0/36
- best_cell: window_weeks=26, low_idx=10.0, BTC/USDT, low-vol, Sharpe 2.12 (crypto, not meaningful)
- worst_cell: window_weeks=78, low_idx=10.0, UUP, low-vol, Sharpe -1.12

## Primary-config validation (FXE, window_weeks=52, low_idx=20.0)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | -0.065 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.091 | ≤ 0.25 | PASS |

Decisive Sharpe fail — no further validators run (Step 7 skip-subset
guidance).

## Decision: REJECTED

The intended asset class (Euro FX / FXE) fails: near-zero/negative Sharpe
and only 2/54 grid cells pass. The min-max "COT Index" normalization
technique does not appear to carry more signal than the percentile-rank
technique used elsewhere this trigger — if a future loop revisits FX COT
data, consider a different currency pair (JPY, GBP) or a trend-confirmation
framing (as with Gold -038) rather than contrarian-fade before abandoning
this data source for FX entirely.
