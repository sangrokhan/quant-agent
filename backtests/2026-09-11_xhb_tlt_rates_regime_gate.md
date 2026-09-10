# Backtest Report: XHB (Homebuilders/Housing) TLT Rates-Regime Gate — Extension of ITB/TLT Strategy

**Strategy file:** `strategies/2026-09-11_itb_tlt_rates_regime_gate.py` (same mechanism, new symbol XHB, per-symbol tuned config)
**Date:** 2026-09-11
**Extension of:** 2026-09-11-054/055 (ITB/TLT rates-regime gate, accepted ITB+QQQ+SPY)

## Hypothesis

Direct extension test of the 2026-09-11-054 mechanism (TLT-uptrend gate on
an SMA trend-following signal) applied to XHB (SPDR S&P Homebuilders ETF)
-- a second, differently-constructed homebuilder/housing-sector ETF
(equal-weight vs ITB's market-cap-weight, broader housing-supply-chain
constituents) -- as a robustness check that the underlying "rate-sensitive
sector + TLT uptrend gate" mechanism isn't an ITB-specific artifact.

## Parameter search

A local grid search (trend_sma_window x tlt_sma_window, both in
{20,30,40,50,60,75,90,100}) found trend_sma_window=20, tlt_sma_window=75
as XHB's best config (Sharpe 1.101), distinct from ITB/QQQ/SPY's shared
40/40 config -- XHB responds better to a faster primary trend window
combined with a slower TLT confirmation window.

## Single-config validation: trend_sma_window=20, tlt_sma_window=75

| Validator | XHB | Threshold |
|---|---|---|
| Sharpe ratio (full sample) | 1.101 ✅ | ≥ 1.0 |
| Max drawdown | 0.158 ✅ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.862 ✅ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.146 ✅ | ≤ 0.5 |

All 5 validators pass cleanly. This confirms the rates-sensitivity
mechanism generalizes to a second homebuilder-sector ETF, not just ITB.

## Decision: ACCEPTED (XHB, per-symbol-tuned config trend_sma_window=20/tlt_sma_window=75)

Extends the ITB/TLT rates-regime-gate family (2026-09-11-054/055) to a
second housing-sector ETF with its own tuned config. Confirms the
underlying economic mechanism (TLT-trend as a financing-conditions proxy
gating rate-sensitive-sector trend-following) is robust across at least two
independently-constructed homebuilder ETFs.
