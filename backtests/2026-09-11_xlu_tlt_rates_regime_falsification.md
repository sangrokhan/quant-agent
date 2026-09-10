# Backtest Report: XLU (Utilities) TLT Rates-Regime Gate — Falsification Test

**Strategy file:** `strategies/2026-09-11_itb_tlt_rates_regime_gate.py` (same mechanism, symbol XLU)
**Date:** 2026-09-11
**Falsification/boundary test of:** 2026-09-11-054/055/056 (ITB/XHB TLT rates-regime gate family)

## Hypothesis

Utilities (XLU) are also commonly described as "bond proxies" sensitive to
interest rates (per Google SERP snippets on XLU/TLT correlation and
"Interest Rates and Utilities" commentary), so testing whether the same
TLT-uptrend-gated SMA trend-following mechanism that worked for homebuilder
ETFs (ITB, XHB) also works for XLU -- as a boundary test of how broadly the
"rate-sensitive sector + TLT gate" mechanism generalizes.

## Parameter search

Local grid search (trend_sma_window x tlt_sma_window, both in
{20,30,40,50,60,75,90,100}): best config trend_sma_window=20,
tlt_sma_window=75, Sharpe only 0.469 -- decisively below the 1.0 threshold,
with every other combo tested even worse.

## Decision: REJECTED (decisive, XLU)

Unlike ITB and XHB (both cleanly accepted), XLU shows no meaningful edge
under this mechanism (best Sharpe 0.469 vs 1.0 threshold, no near-miss).
This is a useful boundary finding: utilities' "bond proxy" behavior is
apparently driven by a different mechanism (dividend-yield competition with
bonds, defensive/low-beta character) than homebuilders' direct
mortgage-affordability channel -- XLU is already low-volatility/defensive
by construction, so a trend-following-style strategy captures little
incremental edge from adding a TLT gate, whereas homebuilders (higher-beta,
more genuinely rate-cyclical) benefit substantially. Confirms the
rates-regime-gate family (2026-09-11-054/055/056) is specifically a
housing/mortgage-sensitivity story, not a generic "any bond-correlated
sector" story -- worth noting for future sector-selection in this lineage.
