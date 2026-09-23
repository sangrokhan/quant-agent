# Garman-Klass Volatility Compression-Breakout with ATR Trail

**Strategy file:** `strategies/2026-09-24_garman_klass_compression_breakout.py`
**Date:** 2026-09-24
**Sources:**
- https://breakingdownfinance.com/finance-topics/risk-management/garman-klass-volatility/ (GK estimator formula)
- https://pinescriptforge.com/strategy/garman-klass-volatility (disclosed compression-breakout-with-ATR-trail rule)

## Hypothesis

GK volatility (4-price OHLC estimator, more efficient than close-to-close
or Parkinson H/L-only) compresses to a low percentile then expands;
breaking price out of the compression range by >=1 ATR in that expansion
window signals a breakout worth trading, trailed by 1.5-2x ATR and exited
when GK volatility itself starts contracting again. First Garman-Klass
strategy in this repo (0 prior KB hits).

## Grid test (Step 6)

`param_grid`: `compression_pctile` in {0.15,0.20,0.30}, `breakout_atr_mult`
in {0.5,1.0,1.5}, `atr_trail_mult` in {1.5,2.0}; symbols equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; `vol_regime_splits=3`. 216 cells total.

- **pass_fraction: 0.315** (68/216)
- **by_asset_class:** equity 6/108 (0.056), crypto 62/108 (0.574) -- strongly crypto-favored (opposite of most strategies in this KB).
- **by_vol_regime:** low 20/72 (0.278), mid 42/72 (0.583), high 6/72 (0.083) -- edge concentrated in mid-vol regime.
- **best cell:** crypto/ETH-USDT, compression_pctile=0.15, breakout_atr_mult=0.5, atr_trail_mult=1.5, mid-vol regime, Sharpe 2.24.

A local sweep around the crypto-best region found full-sample best config
(compression_pctile=0.15, breakout_atr_mult=1.5, atr_trail_mult=2.0):
BTC/USDT full-sample Sharpe only 0.226, ETH/USDT 0.201 -- the mid-vol-tercile
edge does NOT generalize to the full sample.

## Validators (Step 7) — config: compression_pctile=0.15, breakout_atr_mult=1.5, atr_trail_mult=2.0

| Symbol | Sharpe | MDD | Trades |
|---|---|---|---|
| BTC/USDT | 0.226 (**fail**, thr 1.0) | 0.112 (pass) | 718 |
| ETH/USDT | 0.201 (**fail**, thr 1.0) | 0.147 (pass) | 746 |

## Decision (Step 8)

**Rejected — decisively, all symbols.** Despite a promisingly high grid
pass_fraction on crypto (0.574) concentrated in the mid-vol tercile, the
full-sample Sharpe on both BTC/USDT and ETH/USDT collapses far below
threshold (0.23/0.20 vs 1.0) with very high turnover (718-746 trades over
the sample), meaning the tercile-level edge does not survive out of that
narrow slice or the associated transaction costs. Not pursued further this
iteration (skipped walk-forward/parameter-sensitivity given the decisive
full-sample Sharpe failure and normal/light workload budget for this
iteration).
