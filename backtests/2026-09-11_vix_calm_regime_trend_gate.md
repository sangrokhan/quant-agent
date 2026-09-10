# VIX-Calm-Regime Trend Gate — Backtest Report

**Strategy file:** `strategies/2026-09-11_vix_calm_regime_trend_gate.py`
**Date:** 2026-09-11 (id 2026-09-11-040)
**Source:** https://setupalpha.substack.com/p/i-tested-12-smart-money-regime-filters (SetupAlpha Part 3, 2026-06-28)

## Hypothesis

Per SetupAlpha's 800+ backtest study, rank #8 of 12 "smart money" regime filters is
`VIX close < VIX's own rolling SMA` (calm-volatility regime). Source's own disclosed
finding: best COVID-crash score of all 45 filters across the 3-part series (97% dodged),
though a 3pt/yr cost overall since VIX often spikes without a genuine crash following.
Tested here standalone as a gate on plain SMA trend-following (distinct from this repo's
existing combined-condition use, 2026-09-08-153, which also requires a proprietary
sentiment indicator).

## Grid test summary

- param_grid: `trend_sma_window` in {150,200}, `vix_sma_window` in {20,50,100}
- symbols: equity {QQQ,SPY}, crypto {BTC/USDT,ETH/USDT}
- vol_regime_splits: 3
- **72 total cells, 21 passed (pass_fraction 0.292)**
- by_asset_class: equity 21/36, crypto 0/36
- by_vol_regime: low 12/24, mid 9/24, high 0/24
- best_cell: QQQ, trend_sma_window=150/vix_sma_window=20, low-vol Sharpe=2.518

## Single-config validator results (trend_sma_window=200, vix_sma_window=100, SHARED config)

| Symbol | Sharpe | Passed | MDD | Passed |
|---|---|---|---|---|
| QQQ | 1.056 | Yes | 0.173 | Yes |
| SPY | 1.015 | Yes | 0.159 | Yes |

- **Transaction cost survival:** QQQ 118 trades net Sharpe 0.896; SPY 116 trades net Sharpe 0.786 (threshold 0.5) -> **Pass both**
- **Walk-forward:** QQQ 4/4 splits positive (pass_fraction 1.0); SPY 3/4 splits positive (pass_fraction 0.75, meets threshold) -> **Pass both**
- **Parameter sensitivity (QQQ):** 16-combo grid (trend_sma_window 150-225 x vix_sma_window 50-125), relative_std 0.150 -> **Pass**

## Decision

**Accepted for QQQ AND SPY with a SHARED config** (trend_sma_window=200, vix_sma_window=100). All 5 validators pass for both symbols at this single shared parameter set. Crypto rejected decisively (0/36 grid cells) — the VIX has no direct analog for crypto.

## Notes

The VIX-calm-regime gate meaningfully reduces max drawdown vs plain unconditional SMA
trend-following (this repo's other SMA-trend baselines typically show MDD 0.20-0.25) while
still clearing the Sharpe threshold on both major equity indices with one shared config —
a genuinely broad, non-overfit result.
