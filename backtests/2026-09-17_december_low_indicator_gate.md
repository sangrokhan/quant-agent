# Backtest report: December Low Indicator (DLI) risk-off gate

**Strategy file:** `strategies/2026-09-17_december_low_indicator_gate.py`

## Hypothesis

Per Lucien Hooper's December Low Indicator (1970s), confirmed via Google
SERP + direct blog read this iteration (Jeffrey Hirsch commentary,
https://time-price-research-astrofin.blogspot.com/2026/03/us-stock-
indexes-trigger-rare-march.html, explicitly restating Hooper's original
rule and its historical statistics): if the Dow/S&P closes below its prior
December's closing low at any point during Q1 of the current year, this
historically precedes further average declines of ~13.5% (S&P) from the
trigger point. Operationalized as a risk-off regime gate on a primary
SMA(trend_window) trend-following signal: track prior-December's closing
low, flip to flat for the remainder of the Jan-check_end_month window if
price closes below it, reset each new year. First December Low Indicator
entry in this repo (0 prior matches) -- genuinely distinct from
Turn-of-Month/Santa-Claus/Presidential-Cycle/Pre-FOMC-Drift (none
reference a prior-year price level as the trigger).

## Grid test summary (Step 6)

`param_grid={"trend_window": [20,40,60], "check_end_month": [3,4,6]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 36, **pass_fraction: 33.3%**
- by_asset_class: equity 27/54; crypto 9/54
- by_vol_regime: low 27/36; mid 8/36; high 1/36
- best_cell: ETH/USDT, mid-vol regime, trend_window=60/check_end_month=6, Sharpe 2.84
  (crypto has no genuine "December" seasonal structure -- this cell's
  strength is best attributed to the underlying SMA(60) trend-following
  baseline, since the DLI gate for crypto is testing whether US-equity
  seasonality transfers to crypto, which is economically unmotivated)

## Single-config validators (trend_window=40, check_end_month=4, the
source's own "first quarter" framing), full sample 2019-2026

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | pass 1.040 | pass 1.132 |
| Max Drawdown (<=0.25) | pass 0.192 | pass 0.118 |
| TC survival (net Sharpe >=0.5, 5bps/trade) | pass 0.949 (128 trades) | pass 1.021 (119 trades) |
| Walk-forward (4-split) | pass 0.75 (3/4) | pass 1.00 (4/4) |
| Parameter sensitivity (trend_window in [20..50]) | pass 0.055 | pass 0.062 |

## Decision: ACCEPTED (equity QQQ + SPY, shared config); crypto NOT PURSUED

Both equity symbols pass all 5 validators with a single shared config,
non-fragile (parameter sensitivity relative_std <0.07 both). Crypto is
deliberately not pursued as a genuine target for this strategy: the
December Low Indicator's economic rationale (Q1 seasonality tied to
year-end tax-loss-selling reversal / January effect dynamics specific to
US equity markets) has no analogous mechanism for crypto, and the grid's
9/54 crypto passes likely reflect the underlying SMA baseline rather than
the DLI gate itself -- recording this scope limitation explicitly rather
than force-fitting a result without economic grounding.
