# Pre-Month-End Momentum Window (D-10 to D-5), Trend-Sign Gated

**Strategy file:** `strategies/2026-09-24_pre_monthend_momentum_window.py`
**Date:** 2026-09-24
**Source:** https://quantpedia.com/sectoral-intramonth-momentum-cycle/ (Quantpedia, Aug 2026, "Sectoral Intramonth Momentum Cycle")

## Hypothesis

Quantpedia documents a 3-legged intramonth calendar+momentum interaction in
9 Select Sector SPDR ETFs vs SPY. Leg 3 (pre-month-end momentum, days D-10
to D-5) is the only leg not requiring a full cross-sectional multi-ETF
long/short construction -- adapted here to single-asset granularity: long
only during the D-10-to-D-5 window AND when the asset's own trailing
252-day return is positive.

## Grid test (Step 6)

`param_grid`: `mom_window` in {126,189,252}, `window_start` in {8,10,12},
`window_end` in {3,5,7}; symbols equity {QQQ, SPY}, crypto {BTC/USDT,
ETH/USDT}; `vol_regime_splits=3`. 324 cells total.

- **pass_fraction: 0.157** (51/324)
- **by_asset_class:** equity 46/162 (0.284), crypto 5/162 (0.031) -- categorically weaker on crypto.
- **by_vol_regime:** low 48/108 (0.444), mid 0/108 (0.000), high 3/108 (0.028) -- edge exists almost exclusively in the low-vol tercile.
- **best cell:** equity/SPY, mom_window=252, window_start=8, window_end=3, low-vol regime, Sharpe 2.16.
- **worst cell:** equity/QQQ, mom_window=189, window_start=10, window_end=3, high-vol regime, Sharpe -1.66.

## Validators (Step 7) — primary config: mom_window=252, window_start=8, window_end=3

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity (rel. std) | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.361 (**fail**, thr 1.0) | 0.143 (pass) | 0.229 (**fail**, thr 0.5) | 0.75 (pass, 3/4) | 1.029 (**fail**, thr 0.5) | 158 |
| SPY | 0.153 (**fail**) | 0.162 (pass) | -0.014 (**fail**) | 0.75 (pass, 3/4) | 4.997 (**fail**) | 156 |

## Decision (Step 8)

**Rejected — decisively, both symbols.** Full-sample Sharpe collapses far
below threshold on both QQQ and SPY (0.36 / 0.15 vs 1.0), transaction-cost
survival fails outright, and parameter sensitivity is extremely fragile
(relative std 1.0-5.0 vs 0.5 threshold) -- the grid-best low-vol-tercile
cell (Sharpe 2.16) does not generalize to the full sample or across
parameter perturbations. The single-asset trend-sign gate is a much weaker
signal than the source's cross-sectional sector-rank construction; genuine
replication of the source's edge would require the multi-ETF long/short
architecture this repo's `generate_returns_fn(price_df, **params)` contract
does not support (same feasibility limitation flagged for prior
sector-rotation entries).
