# Backtest Report: Savitzky-Golay-Smoothed Trend Filter (edge-preserving signal smoothing)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_savgol_smoothed_trend_filter.py`
**Source:** Marc Weibel, "Edge-Preserving Macro-Financial Signal Extraction
for Real-Time U.S. Sector Rotation" (2026), summarized in Quantitativo
Weekly #3, https://www.quantitativo.com/p/quantitativo-weekly-3 (read via
browser_exec after web_extract failed with the DuckDuckGo
search-only-backend error).

## Hypothesis

The source paper finds that smoothing a sector-rotation signal with a
causal, edge-preserving filter (Savitzky-Golay, Perona-Malik) before
thresholding roughly doubles-to-triples Sharpe vs. trading the raw signal
directly (0.304 raw -> 0.707 Savitzky-Golay -> 0.820 Perona-Malik), because
edge-preserving filters "smooth inside a regime but keep the jumps between
regimes," cutting whipsaw/turnover substantially. Adapted to this repo's
simplest available trend proxy: price-vs-SMA momentum score, smoothed with
a one-sided (causal, no lookahead) Savitzky-Golay filter before the
long/flat threshold, rather than porting the source's exact 4-signal
macro/sector-ETF setup (not available in this repo's OHLCV-only data).

## Grid test summary (Step 6)

`param_grid={"sma_window":[30,50], "sg_window":[11,21,31]}` (polyorder
fixed at 2), `symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 72, **passed:** 16, **pass_fraction: 0.222**
- **by_asset_class:** equity 16/36; crypto 0/36 (decisive reject)
- **by_vol_regime:** low 12/24, mid 4/24, high 0/24 — no cells pass in the
  high-vol tercile
- **best_cell:** QQQ, sma_window=50, sg_window=11, low-vol regime, Sharpe
  2.80; **worst_cell:** the SAME config (sma_window=50, sg_window=11),
  QQQ, high-vol regime, Sharpe -0.95 — extreme regime-dependence within
  the identical parameter combo

## Single-config validation (Step 7): sma_window=50, sg_window=11, polyorder=2

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.604 (**FAIL**) | 0.465 (**FAIL**) | >= 1.0 |
| Max drawdown | 0.344 (**FAIL**) | 0.298 (**FAIL**) | <= 0.25 |
| TC survival (5bps/trade) | 0.561 (PASS, 83 trades) | 0.402 (**FAIL**, 95 trades) | >= 0.5 |
| Walk-forward (4 manual chunks) | 0.75 (PASS, borderline) | 0.75 (PASS, borderline) | >= 0.75 |
| Parameter sensitivity (relative_std, 6-combo grid) | 0.134 (PASS) | 0.277 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug.)

## Decision: REJECT

Sharpe and MDD both fail full-sample on both QQQ and SPY, and SPY also
fails TC survival. The best grid cell's own worst-cell counterpart (same
exact parameters, different vol regime) swings from Sharpe +2.80 to -0.95,
confirming this is a highly regime-dependent signal rather than a broadly
robust edge — consistent with 0/24 high-vol-regime cells passing anywhere
in the grid. The core mechanism from the source paper (edge-preserving
smoothing improves on a raw signal) may still be valid in its original
4-signal macro/sector-rotation context, but the single-SMA-crossover proxy
used here is simply a weak base signal to begin with (this repo has
rejected numerous single-SMA/EMA crossover trend-following variants
already) — smoothing a weak signal does not manufacture a strong one.
Crypto rejected decisively (0/36). Not worth revisiting without access to
the source's actual macro/sector-ETF signal inputs (VIX, Russell/SPX
ratio, discretionary/staples, financials/utilities), which this repo's
current data/loaders.py does not provide.
