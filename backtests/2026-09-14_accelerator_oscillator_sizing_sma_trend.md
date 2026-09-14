# Accelerator Oscillator Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-174 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_accelerator_oscillator_sizing_sma_trend.py`
**Status:** REJECTED (all 4 symbols) -- kept as a record per Step 8.

## Hypothesis

Accelerator Oscillator (AC, Bill Williams): AO = SMA(median_price,5) -
SMA(median_price,34); AC = AO - SMA(AO,5) -- the acceleration/deceleration
of AO's own momentum, already zero-centered. This repo has 1 prior AC
entry (2026-09-06, binary zero-line crossover + min-hold gate). This
iteration reframes AC as a CONTINUOUS SIZING dial, distinct from this cron
trigger's own already-tested continuous-sizing AO (2026-09-14-173, AO's
level) since AC is a second-derivative-like acceleration signal. First AC
continuous-sizing variant in this repo.

Source: Google AI-overview synthesis (browser_exec fallback -- web_search
DDGS backend returned "No results found" for the prior iteration's query)
of TradingView/StocksTrader's AC formula pages.

## Grid test summary (Step 6)

`param_grid={ac_smooth_window: [5,10], sensitivity: [0.4,0.6,0.8]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 41, **pass_fraction:** 0.569.
- **by_asset_class:** equity 18/36 (0.500), crypto 23/36 (0.639) -- crypto
  outperforms equity in the grid, an unusual pattern this cron trigger
  (also seen with Chaikin Volatility, 2026-09-14-172, which similarly
  didn't survive full-sample validation).
- **by_vol_regime:** low 24/24 (1.000), mid 12/24 (0.500), high 5/24 (0.208).
- **best_cell:** ETH/USDT, ac_smooth_window=5/sensitivity=0.4, mid-vol,
  Sharpe 2.546.
- **worst_cell:** ETH/USDT, ac_smooth_window=5/sensitivity=0.8, high-vol,
  Sharpe 0.076 (mildest worst_cell this cron trigger -- notably not
  negative).

## Single-config validator results (Step 7)

Best grid config (ac_smooth_window=5, sensitivity=0.4) tested full-sample
per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.056 (pass) | 0.090 (pass) | 0.243 (**fail**, decisive) | 1.000 (pass) | 0.041 (pass) | **rejected** |
| SPY | 1.054 (pass) | 0.067 (pass) | 0.133 (**fail**, decisive) | 1.000 (pass) | 0.069 (pass) | **rejected** |
| BTC/USDT | 0.184 (**fail**, decisive) | 0.272 (**fail**) | -0.063 (**fail**) | 1.000 (pass) | 0.057 (pass) | **rejected** |
| ETH/USDT | 0.153 (**fail**, decisive) | 0.222 (pass) | -0.063 (**fail**) | 1.000 (pass) | 0.136 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** QQQ and SPY both clear Sharpe/MDD/walk-forward
individually but decisively fail transaction-cost survival (0.243/0.133 vs
0.5) -- AC is a "second derivative" of median-price momentum (AO's own
deviation from its SMA5), making it highly reactive/noisy, driving high
sizing-dial turnover that erodes net returns after costs, the same failure
mode already documented for Chaikin Volatility (2026-09-14-172, also a
rate-of-change-of-a-smoothed-series construction). Crypto fails Sharpe/MDD/
TC-survival decisively despite the grid's promising crypto pass_fraction --
another instance where the tercile-level grid pass rate did not transfer to
full-sample single-config validation. This adds a second confirmed data
point (after Chaikin Volatility) supporting the emerging finding: indicators
built as a rate-of-change/acceleration OF an already-smoothed oscillator
(rather than a single-smoothing-stage oscillator) tend to fail the
continuous-sizing-dial technique on transaction-cost grounds, even when
their Sharpe/MDD/walk-forward look fine individually.
