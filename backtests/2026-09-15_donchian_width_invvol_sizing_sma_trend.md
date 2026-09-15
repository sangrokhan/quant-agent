# Backtest Report: Inverse Donchian Channel Width Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_donchian_width_invvol_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-040

## Hypothesis

Donchian Channel Width (per sdk-trading.com's formula breakdown, visited
this iteration): upper=HighestHigh(N), lower=LowestLow(N), width=upper-lower
— the raw range spanned by the current rolling window's price extremes,
fundamentally different from stdev-based volatility measures. No
first-party numeric trading rule was found (descriptive page only), so
this iteration applies this repo's own established "compression -> scale
exposure up, expansion -> scale exposure down" logic: normalized width
(width/close) is min-max normalized over a rolling window and INVERTED,
used as a continuous sizing dial inside an SMA(trend_window) uptrend gate
with deadband. First Donchian-Width-specific strategy in this repo
(distinct from existing Donchian *breakout* entries that use channel
boundary levels, not width, as the trigger).

## Step 6 — Grid summary (donchian_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `donchian_window in [10, 20, 30]`, `sensitivity in [0.5, 0.8]`,
  symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
  `vol_regime_splits=3`.
- **72 cells, 29 passed (pass_fraction = 0.403)**.
- By asset class: equity 18/36, crypto 11/36 (default leverage_cap=1.0
  overleverages crypto, penalizing MDD in this scan — addressed in Step 7
  via a per-symbol leverage cap retune).
- By vol regime: low 19/24, mid 6/24, high 4/24 — same familiar pattern of
  edge concentrated in calmer regimes.
- Best cell: ETH/USDT, donchian_window=30, sensitivity=0.5, mid-vol
  regime, Sharpe 2.51.
- Worst cell: QQQ, donchian_window=10, sensitivity=0.5, high-vol regime,
  Sharpe -0.19.

## Step 7 — Single-config validator suite (per-symbol retuned)

Equity config: `donchian_window=20, sensitivity=0.5, trend_window=40,
minmax_window=100, base_exposure=0.4, leverage_cap=1.0, deadband=0.5`.

Crypto config (leverage-cap-aware retune to fix MDD, following this repo's
established per-symbol/per-asset-class parameter retune pattern):
`donchian_window=20, sensitivity=0.5, trend_window=40, minmax_window=100,
base_exposure=0.24, leverage_cap=0.4, deadband=0.1`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 0.984 (fail, <1.0) | 0.139 (pass) | 0.661 (pass) | 0.75 (pass) | 0.108 (pass) | No (Sharpe near-miss) |
| SPY | 0.817 (fail) | 0.087 (pass) | 0.476 (fail) | 1.00 (pass) | 0.072 (pass) | No |
| BTC/USDT | 1.181 (pass) | 0.215 (pass) | 0.765 (pass) | 1.00 (pass) | 0.012 (pass) | **Yes** |
| ETH/USDT | 1.227 (pass) | 0.248 (pass) | 0.935 (pass) | 1.00 (pass) | 0.038 (pass) | **Yes** |

Walk-forward used the repo's established manual 4-equal-slice fallback
(`vbt.utils.splitting` unavailable in the installed vectorbt version).

## Step 8 — Decision: **ACCEPT (crypto only: BTC/USDT, ETH/USDT)**

Both crypto symbols pass all 5 validators cleanly with a tight
parameter-sensitivity margin (rel std 0.01-0.04) at
`leverage_cap=0.4, base_exposure=0.24, deadband=0.1`. Equity (QQQ, SPY)
does not pass — QQQ is a Sharpe near-miss (0.984 vs 1.0), SPY fails both
Sharpe and TC-survival. Strategy file and grid config remain live in
`strategies/` for the crypto scope only; equity use is explicitly
out-of-scope per this validator run.
