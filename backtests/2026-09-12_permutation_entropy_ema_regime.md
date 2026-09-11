# Permutation-Entropy Regime-Gated EMA Crossover

**Hypothesis:** Permutation Entropy (PE, Bandt & Pompe 2002) measures
market "order" vs "chaos" via Shannon entropy of ordinal rank patterns of
price windows. Per https://kr.tradingview.com/script/wPxhw6y6-Permutation-Entropy-Complexity-Oscillator/
(GospodarValovaHR, via browser_exec/google.com fallback; web_search DDGS
backend TLS/connection errors this iteration): low PE = structured/trending
regime (good for trend-following entries), high PE = chaotic/choppy regime
(avoid trend entries). Operationalized as: gate a fast/slow EMA crossover
trend-following signal so entries fire only when rolling PE <= threshold.

Source: https://kr.tradingview.com/script/wPxhw6y6-Permutation-Entropy-Complexity-Oscillator/
(via browser_exec fallback).

## Step 6 Grid Test Summary (48 cells: 2 pe_threshold x 2 fast_ema x 1
slow_ema x 4 symbols x 3 vol regimes)

- pass_fraction: 0.125 (6/48)
- by_asset_class: equity 6/24 passed, crypto 0/24 (decisively rejected)
- by_vol_regime: low 6/16, mid 0/16, high 0/16 (edge ONLY in low-vol
  regime, zero pass elsewhere)
- best_cell: pe_threshold=0.9, fast_ema=20, slow_ema=50, QQQ, low-vol
  regime, Sharpe=1.40
- worst_cell: pe_threshold=0.9, fast_ema=10, slow_ema=50, SPY, high-vol
  regime, Sharpe=-1.49

## Step 7 Single-Config Validation (best config: pe_threshold=0.90,
fast_ema=20, slow_ema=50, full sample 2019-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|--------|--------|-----|-------------|---------------|---------------------|
| QQQ | -0.229 (FAIL) | 0.365 (FAIL, thr 0.25) | -0.290 (FAIL) | 0.50 (FAIL) | 1.64 rel std (FAIL) |
| SPY | -0.016 (FAIL) | 0.205 (PASS) | -0.110 (FAIL) | 0.50 (FAIL) | 0.95 rel std (FAIL) |

## Decision: REJECTED (decisively)

Full-sample Sharpe is negative on both QQQ and SPY at the grid-best config
-- the grid's apparent edge was entirely a low-vol-tercile artifact that
does not survive full-sample validation once mid/high-vol periods are
included (grid showed 0/16 passes in both mid and high vol regimes). Also
fails max-drawdown on QQQ, transaction-cost survival on both, walk-forward
on both, and parameter sensitivity is highly unstable (relative std 1.64
on QQQ, meaning Sharpe swings wildly across nearby pe_threshold values).
Crypto decisively rejected (0/24 grid cells). No further follow-up
recommended -- this is a clean rejection, not a near-miss.
