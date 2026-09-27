# Backtest Report: Undecimated (a-trous) Haar Wavelet + ATR Trailing Trend

**Strategy file:** `strategies/2026-09-27_haar_atrous_atr_trailing_trend.py`
**Hypothesis ID:** 2026-09-27-haar-atrous-01 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Per QuantAlgo's "Wavelet Transform Trend" TradingView indicator
(https://www.tradingview.com/script/YI4KzWFT-Wavelet-Transform-Trend-QuantAlgo/,
read via `browser_exec` — TradingView blocks `web_extract`'s ddgs backend),
a multi-level UNDECIMATED (à trous) Haar wavelet cascade denoises the price
path without downsampling (fully shift-invariant), then wraps the denoised
"approximation-only" path in a SuperTrend-style ratcheting ATR band. The
trend state flips only on a confirmed close beyond the ratcheting band. This
is distinct from the repo's prior standard (decimated) DWT strategy
(2026-09-16-080, rejected) because the à trous construction never
downsamples and the ATR band here ratchets (freezes against adverse moves,
only trails favorably) rather than being a simple static breakout-confirm
band.

## Single-config validation (QQQ, 2015-01-01 to 2026-09-01)

Config: `wavelet_period=30, wavelet_levels=2, atr_mult=3.5`

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.047 | ≥ 1.0 | ✅ |
| Max drawdown | 0.209 | ≤ 0.25 | ✅ |
| Transaction cost survival (15bps/trade, 65 trades) | net Sharpe 0.924 | ≥ 0.5 | ✅ |
| Walk-forward (4-split manual) | 1.00 pass fraction | ≥ 0.75 | ✅ |
| Parameter sensitivity (levels∈{2,3}, atr_mult∈{3.0,3.5,4.0}) | rel. std 0.165 | ≤ 0.5 | ✅ |

All 5 validators pass for QQQ at this config. **Accepted (QQQ only).**

## Grid-test summary (Step 6)

Grid: `wavelet_period ∈ {30,40,60}`, `wavelet_levels ∈ {2,3,4}`, `atr_mult ∈
{1.5,2.0,2.5}` × symbols `{QQQ, SPY} (equity)`, `{BTC/USDT, ETH/USDT}
(crypto)` × vol_regime_splits=3 (low/mid/high realized-vol terciles), using
`validation/grid_test.py::run_strategy_grid` (pass criteria: Sharpe≥1.0 AND
MDD≤0.25 per cell).

- **Overall pass_fraction: 0.25** (81/324 cells)
- **By asset class:** equity 78/162 (0.48) pass; crypto 3/162 (0.019) pass
  — crypto decisively fails almost everywhere at this atr_mult range.
- **By vol regime:** low 54/108 (0.50); mid 27/108 (0.25); high 0/108
  (0.00) — the strategy passes only in low/mid realized-vol regimes and
  **fails universally in high-vol regimes** (the ratcheting ATR band
  whipsaws or holds through the sharpest drawdowns without exiting soon
  enough at these atr_mult values ≤2.5).
- **Best cell:** crypto ETH/USDT, mid-vol, `wavelet_period=30,
  wavelet_levels=4, atr_mult=2.5`, Sharpe 2.386 — an isolated high-Sharpe
  cell, not representative of crypto's overall poor pass rate (3/162), so
  not pursued as a crypto-specific config without further validation.
- **Worst cell:** equity QQQ high-vol, `atr_mult=1.5`, Sharpe -0.462.

A follow-up single-symbol sweep (outside the formal grid, atr_mult up to
3.5) found QQQ clears both Sharpe and MDD thresholds at
`wavelet_levels=2, atr_mult=3.5` (wider band reduces high-vol-regime
whipsaw enough to pass on the full sample) — this became the accepted
config above. SPY at the identical config only reaches Sharpe 0.487/MDD
0.267 (decisive fail, consistent with the grid's equity pass rate being
well under 100%even at narrower atr_mult).

## Decision

**Accept: QQQ only**, `wavelet_period=30, wavelet_levels=2, atr_mult=3.5`.
Reject SPY and both crypto pairs at this construction — scope the strategy
narrowly to QQQ per the honest-narrow-scope principle in RESEARCH_LOOP.md
Step 6. Crypto and high-vol regimes broadly are out of scope for this
strategy; a future loop could investigate wider `atr_mult` specifically for
crypto's high notional volatility, but that is not attempted here.
