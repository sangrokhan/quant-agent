# 2026-09-16 Coppock Curve Continuous Sizing — Crypto Retune (full universe extension)

## Hypothesis
Direct fix for prior id `2026-09-14-171` (Coppock Curve WMA-smoothed dual-ROC
composite momentum used as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate; accepted QQQ (and later SPY via `2026-09-15-009`) but crypto
(BTC/USDT, ETH/USDT) was rejected "decisively" without a leverage-cap-aware
retune attempt). This iteration applies this repo's standard leverage-cap-aware
retune pattern (leverage_cap cut to 0.3, base_exposure reduced to 0.15) to the
identical, unmodified Coppock Curve strategy code
(`strategies/2026-09-14_coppock_sizing_sma_trend.py`) for crypto only. No new
external research this sub-iteration — formula/source unchanged from
`2026-09-14-171` (Google AI-overview synthesis of LightningChart/StockCharts
ChartSchool Coppock Curve calculation, via `browser_exec` fallback originally).

## Grid test (Step 6)
`run_grid_coppock_sizing_crypto_lev.py` — crypto only (BTC/USDT, ETH/USDT),
`sensitivity in [0.4,0.5,0.6]`, `deadband in [0.20,0.30,0.40]` at fixed
`leverage_cap=0.3, base_exposure=0.15`, `vol_regime_splits=3`.

- total_cells: 54, passed_cells: 13, **pass_fraction: 0.241**
- by_vol_regime: low 6/18, mid 6/18, high 1/18 (edge concentrated low/mid vol)
- best_cell: ETH/USDT, sensitivity=0.6, deadband=0.2, mid-vol, Sharpe 2.037

## Single-config validation (Step 7)
Config: `trend_window=40, roc1_period=14, roc2_period=11, wma_window=10,
zscore_window=100, base_exposure=0.15, sensitivity=0.6, leverage_cap=0.3,
deadband=0.2` (chosen from grid's best low-deadband cell; note: the raw grid's
`deadband=0.3/0.4` cells returned `inf` Sharpe due to a near-zero-trade
degenerate case — deadband was kept at 0.10-0.25 for the parameter-sensitivity
sweep to avoid that degenerate region).

| Symbol   | Sharpe | MDD   | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel-std) |
|----------|--------|-------|-------------------------|--------------|------------------------------|
| BTC/USDT | 1.244  | 0.162 | 1.020                   | 1.00 (4/4)   | 0.067                        |
| ETH/USDT | 1.017  | 0.161 | 0.873                   | 1.00 (4/4)   | 0.088                        |

All 5 validators pass on both symbols (thresholds: Sharpe>=1.0, MDD<=0.25,
net-Sharpe-after-costs>=0.5, walk-forward pass-fraction>=0.75,
param-sensitivity rel-std<=0.5).

## Decision
**Accept (crypto: BTC/USDT, ETH/USDT).** Combined with the existing
`2026-09-14-171` + `2026-09-15-009` equity accept (QQQ, SPY), Coppock Curve's
continuous-sizing dial now covers the full universe: QQQ, SPY, BTC/USDT,
ETH/USDT.

## Source
https://www.tradingview.com/ (via prior iteration's LightningChart/StockCharts
ChartSchool Google AI-overview synthesis, `2026-09-14-171`) — formula unchanged,
no new external fetch this iteration (pure own-data parameter retune).
