# Backtest Report: Rolling-Window Causal Wavelet-Denoised Trend + ATR Confirmation

**Date:** 2026-09-16 (iteration 3, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_wavelet_denoise_trend_atr.py`

## Hypothesis

Per a Google AI-overview summary of wavelet-denoising trend-trading
writeups (Medium/Sofien Kaabar CFA, MDPI, ResearchGate, TradingView): apply
a Discrete Wavelet Transform (Daubechies db4) to the close-price series,
zero out the finest-detail (highest-frequency/noise) coefficients, and
reconstruct a denoised trend path — computed causally on a ROLLING trailing
window at every bar (not a single full-series transform, which would leak
future info backward through boundary coefficients, per the source's own
explicit causal-processing rule). Go long when the denoised trend's slope
turns positive AND price closes outside an ATR band around the
reconstructed trend (source's "confirmation filter" to reject false
breaks). First true Discrete-Wavelet-Transform strategy in this repo
(distinct from the one prior Hilbert-Transform entry and all EMA/Kalman/
Ehlers-chain smoothers already tested — DWT is a non-recursive, block-based
multi-resolution decomposition, a fundamentally different construction).

Source read via `browser_exec` fallback after `web_search`'s DDGS backend
again failed with the same Yahoo/TLS RequestError as this trigger's prior
2 iterations. `pywavelets` was not present in the repo venv and was
installed (`uv pip install pywavelets`) to implement this.

## Grid test summary (Step 6)

`param_grid={wavelet_window: [45,60,75], atr_mult: [0.0,0.25]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`.

- total_cells: 72, passed_cells: 24, **pass_fraction: 0.333**
- by_asset_class: equity 15/36, crypto 9/36 — a rare case where crypto
  also clears bars in the grid at all (most single-config attempts in this
  repo reject crypto decisively), though not on the final full-sample check
- by_vol_regime: low 17/24, mid 7/24, high 0/24 — edge entirely absent in
  high-vol tercile
- best_cell: equity/SPY/low-vol, sharpe 2.49 (wavelet_window=45,
  atr_mult=0.0)
- worst_cell: crypto/ETH-USDT/high-vol, sharpe -0.84

Best balanced full-grid config (highest pass count across both asset
classes): `wavelet_window=60, atr_mult=0.0` (equity 3/6, crypto 2/6 grid
cells passing).

## Single-config validator results (Step 7)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Overall |
|---|---|---|---|---|---|---|
| QQQ | 0.850 (fail, near-miss) | 0.128 (pass) | 0.047 (fail) | 1.00 (pass) | 0.228 rel-std (pass) | REJECT |
| SPY | 0.792 (fail, near-miss) | 0.114 (pass) | -0.092 (fail) | 1.00 (pass) | 0.380 rel-std (pass) | REJECT |
| BTC/USDT | 0.963 (fail, near-miss) | 0.509 (fail) | 0.520 (pass) | 0.75 (pass) | 0.310 rel-std (pass) | REJECT |
| ETH/USDT | 0.713 (fail) | 0.554 (fail) | 0.397 (fail) | 0.75 (pass) | 0.562 rel-std (fail) | REJECT |

## Decision

**Reject across all 4 symbols.** Full-sample Sharpe is a near-miss but
decisive fail on all symbols (0.71-0.96, all below the 1.0 threshold), and
equity net-of-cost Sharpe collapses (QQQ 0.047, SPY actually negative
-0.092) because the per-bar rolling-window DWT recomputation produces a
noisy, high-turnover signal (746 QQQ trades over the sample) that erodes
Sharpe once 10bps/trade costs are applied. Crypto additionally fails MDD
decisively (51-55% vs 25% threshold). The grid's apparent pass_fraction
(0.333, unusually broad for a first-pass strategy) does not survive
full-sample single-config validation — most of the grid's passes come from
the low-vol tercile alone. Strategy file and this report kept as the record
of a rejected attempt; note for future iterations: if revisiting wavelet
denoising, a coarser rebalance cadence (only re-evaluate every N bars
rather than every bar) or an explicit deadband/hysteresis on the trend
slope would likely be needed to control turnover before the transaction-
cost failure can be fixed.
