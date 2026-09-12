# Backtest Report: Bufi Adaptive Oscillator Threshold (BAT) on RSI(2)

**Strategy file:** `strategies/2026-09-12_bufi_adaptive_rsi_threshold.py`
**Date:** 2026-09-12

## Hypothesis

Per Francesco Bufi's "Overbought/Oversold Oscillators: Useless Or Just
Misused" (TASC Traders' Tips, October 2024; fully disclosed Pine v5 source:
https://www.tradingview.com/script/zDP76aFT-TASC-2024-10-Adaptive-Oscillator-Threshold/),
a static RSI buy-threshold ignores trend and volatility context. Bufi's
Adaptive Threshold (BAT) rescales the buy level using a rolling
linear-regression slope (trend, numerator) divided by rolling stdev
(dispersion, denominator), clamped to [-0.5, 0.5]. Applied to RSI(2): long
entry when RSI(2) crosses below `buy_level * adap_k * BAT(close, adap_len)`,
exit after a fixed `exit_bars` (28-bar) time-stop. Source's dollar
stop-loss was omitted (doesn't port to a % return framework).

## Grid test (Step 6) — `grid_result_bufi_adaptive_rsi.json`

Grid: `rsi_len ∈ {2,4}`, `buy_level ∈ {10,14,20}`, `adap_k ∈ {3.0,6.0}` ×
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles (low/mid/high),
2018-01-01 to 2026-09-01. 144 total cells.

- **pass_fraction: 0.1458** (21/144)
- by_asset_class: equity 21/72 passed, **crypto 0/72 passed** (decisive fail)
- by_vol_regime: low 12/48, mid 4/48, high 5/48 — clearly concentrated in
  low-vol regimes
- best_cell: QQQ/SPY-family, `rsi_len=2, buy_level=20, adap_k=6.0`, low-vol,
  Sharpe 2.46 (SPY)
- worst_cell: `rsi_len=4, buy_level=14, adap_k=6.0`, SPY high-vol, Sharpe -0.80

## Standard validators (Step 7) — best config `rsi_len=2, buy_level=20, adap_k=6.0, exit_bars=28`

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.105 (pass, thr 1.0) | 0.203 (pass, thr 0.25) | 1.055 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | rel_std 0.101 (pass, thr 0.5) | **ACCEPT** |
| SPY | 0.796 (**fail**, thr 1.0) | 0.237 (pass) | 0.734 (pass) | 0.75 (pass) | rel_std 0.209 (pass) | REJECT (Sharpe) |

Crypto rejected decisively at the grid stage (0/72 cells), not re-validated
with the full suite.

## Decision

**ACCEPT for QQQ only.** SPY narrowly fails the Sharpe threshold (0.796 vs
1.0) despite passing every other validator — recorded as a near-miss.
Crypto (BTC/USDT, ETH/USDT) rejected decisively; the RSI(2)+BAT combination
does not translate to 24/7 crypto price dynamics in this grid.

Scope note: strategy is honestly narrow — QQQ-only, low/mid-vol-regime
biased (per grid: low-vol 12/48 pass vs high-vol 5/48).
