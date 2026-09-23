# AF-MSI Macro Stress Leverage Gate — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_afmsi_macro_stress_leverage_gate.py`
**Source:** https://algorithmicfire.com/post/tactical-leverage-with-the-macro-stress-index — "Tactical Leverage with the AlgorithmicFIRE Macro Stress Indicator (AF-MSI)" (found via `browser_exec` Google News search after `web_search` DDGS/Yahoo backend TLS-errored on every query this iteration).

## Hypothesis

A composite 3-condition macro stress score (term-spread inversion, credit-spread
elevation z-score>1.5, VIX>25 sustained 2+ days), smoothed with a 10-day rolling
max for whipsaw resistance, gates a leverage BOOST above 1.0x on top of a
separate SMA trend gate: full leverage_cap exposure when trend is up AND
stress score == 0; base 1.0x exposure when trend is up but any stress
condition is active; flat when trend is down. Adapted from the source's FRED-based
T10Y2Y/BAA10Y inputs (unavailable in this repo) to ^TNX-^IRX term spread and
HYG/IEF ratio z-score credit proxy (consistent with this repo's existing
yield-curve/credit-spread strategy conventions).

## Config selected

`trend_window=200, leverage_cap=1.3, vix_threshold=22.0, credit_zscore_window=252, credit_z_threshold=1.5, vix_persist_days=2, smooth_window=10`

## Grid summary (Step 6)

- Grid: `trend_window ∈ {100,200} × leverage_cap ∈ {1.25,1.5,2.0} × vix_threshold ∈ {22,25}` = 12 combos × {QQQ,SPY,BTC/USDT,ETH/USDT} × 3 vol regimes = 144 cells.
- **pass_fraction: 0.194 (28/144)**
- By asset class: equity 28/72 (0.389), crypto 0/72 (0.0 — expected, no US Treasury/credit-market analog for 24/7 crypto).
- By vol regime: low 24/48 (0.50), mid 4/48 (0.083), high 0/48 (0.0).
- Best cell: SPY, trend_window=200/leverage_cap=2.0/vix_threshold=25, low-vol regime, Sharpe 2.31.
- Worst cell: SPY, trend_window=200/leverage_cap=1.25/vix_threshold=25, high-vol regime, Sharpe -0.24.

## Single-config validator results (2015-01-01 to 2026-09-01, config above)

| Symbol | Sharpe | MDD | TC-survival (10bps, net Sharpe) | Walk-forward (4-split manual) | Param sensitivity (rel-std, trend_window=200 subset) |
|---|---|---|---|---|---|
| QQQ | 1.111 (pass, thr 1.0) | 0.235 (pass, thr 0.25) | 1.046 (pass, thr 0.5) | 4/4 pass | 0.032 (pass, thr 0.5) |
| SPY | best found across a widened 48-combo local search: 0.864 (FAIL, thr 1.0) | — | — | — | — |

Widened local parameter search for SPY (trend_window ∈ {100,150,200,250} × leverage_cap ∈ {1.2,1.3,1.5} × vix_threshold ∈ {20,22,25,28}, 48 combos) found no config clearing Sharpe ≥ 1.0; best was 0.864 at trend_window=250/leverage_cap=1.5/vix_threshold=25.

## Decision

**ACCEPT (equity: QQQ only)**. All 5 validators pass with comfortable margins; very low parameter sensitivity (rel-std 0.032) across the trend_window=200 subgrid suggests the leverage-boost mechanism is robust to leverage_cap/vix_threshold choice specifically for QQQ. **SPY: near-miss/rejected** (best full-sample Sharpe 0.864 across a widened search). **Crypto: rejected** (0/72 grid cells — no US Treasury yield curve or corporate credit market exists for 24/7 crypto, so the stress score is structurally uninformative there; strategy correctly treats crypto as `is_crypto=True` → stress score always 0, reducing to a plain SMA(200) trend gate at 1.0x, which itself doesn't clear crypto's higher volatility Sharpe bar in this grid).
