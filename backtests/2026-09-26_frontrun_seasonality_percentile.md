# Backtest Report: Front-Run Seasonality (Percentile-of-Trailing-12mo, X-11 Shift)

**Hypothesis source:** QuantPedia, "Trader's Guide to Front-Running Commodity Seasonality"
https://vvv.quantpedia.com/traders-guide-to-front-running-commodity-seasonality/ (5 Dec 2024,
Cyril Dujava, own-research, free). `web_extract` failed with
"DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content"; read via
`browser_exec` fallback.

**Hypothesis:** Source's naive time-series seasonality model ("Model 1": predict month t+1
using month t+1-12's return rank within its trailing 12mo window) had NEGATIVE Sharpe
(-0.40) on 4 commodity ETFs, 2007-2024, because sophisticated participants front-run the
seasonal signal. Shifting the lookback by one extra month ("Model 2": use month t+1-11
instead of t+1-12) flips this to Sharpe +0.55, CAR +6.71%, MaxDD -20.43%. This repo tests a
single-symbol adaptation of the same time-series (per-instrument, not cross-sectional)
mechanic on QQQ and SPY.

## Grid Test (Step 6)

Params: `shift_months` in {10, 11, 12}, `percentile_threshold` in {0.5, 0.6}.
Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}. vol_regime_splits=3 (low/mid/high
realized-vol terciles). Period 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.278** (20/72 cells passed Sharpe>=1.0 AND MDD<=0.25)
- by_asset_class: equity 19/36 passed; crypto 1/36 passed
- by_vol_regime: low 13/24; mid 6/24; high 1/24 -- almost entirely a low-vol-regime effect
- best_cell: shift_months=12, percentile_threshold=0.6, QQQ, low-vol regime, Sharpe 2.54
- worst_cell: shift_months=11, percentile_threshold=0.5, SPY, mid-vol regime, Sharpe -0.21

Per-vol-regime Sharpe breakdown for the chosen primary config (shift_months=11,
percentile_threshold=0.6): QQQ [low 1.50, mid 1.71, high -0.02]; SPY [low 2.38, mid 0.45,
high 0.30]. Individual regime slices look attractive but this is exactly the kind of grid
result that needs full-sample confirmation before trusting it.

## Full-Sample Validators (Step 7), config shift_months=11, percentile_threshold=0.6

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.549 **FAIL** | 0.536 **FAIL** |
| Max Drawdown (<=0.25) | (passed, not the binding constraint) | 0.296 **FAIL** |
| TC survival (10bps/trade, net Sharpe>=0.5) | net Sharpe ~0.53 borderline | 0.482 **FAIL** |
| Walk-forward | skipped -- `vectorbt.utils.splitting` API unavailable in this env; moot given decisive Sharpe fail | skipped |
| Parameter sensitivity (relative_std<=0.5) | 0.148 PASS | 0.163 PASS |

Full JSON: `validate_result_frontrun_seasonality.json`, grid JSON:
`grid_result_frontrun_seasonality.json`.

## Decision: REJECT

The grid's low-vol-regime cells look strong (Sharpe 1.5-2.5), but full-sample Sharpe
collapses to ~0.54 on both QQQ and SPY -- well short of the 1.0 threshold -- and SPY also
fails max drawdown (0.296 vs 0.25 cap). Parameter sensitivity is fine (the finding is
directionally stable across shift_months=10/11/12), but the strategy simply doesn't clear
the bar across the full sample once mid/high-vol regimes are included. This confirms the
source's own commodity-ETF cross-sectional dispersion effect (percentile RANKING one asset
against several siblings each month) does not translate cleanly into a single-symbol
time-series-only percentile-vs-own-history rule -- the edge may be genuinely
cross-sectional, not per-instrument, contra this repo's single-asset simplification.
Strategy file and this report kept as a record of a rejected attempt.
