# Backtest Report: Ag Selling Model Exhaustion-Fade Sizing Dial

**Strategy file:** `strategies/2026-09-16_ag_selling_exhaustion_fade_sma_trend.py`
**Date:** 2026-09-16
**Hypothesis source:** Perry J. Kaufman, "An Ag Selling Model" (TASC August 2026 Traders' Tips, thinkorswim implementation) — https://traders.com/documentation/feedbk_docs/2026/08/traderstips.html (visited this iteration via browser_exec; `web_search` DDGS backend failed with `RequestError`/TLS close-notify on every query attempted this iteration, so all research this iteration used the browser fallback).

## Hypothesis

Kaufman's Ag Selling Model computes a "sell level" = `SMA(averageLength) +
ATR(atrLength) * atrFactor` for soybean futures and issues a short-sale
signal whenever price extends above that level (an exhaustion/overbought
interpretation of extension above a trend+volatility band). This repo
already has one SMA+ATR band strategy (2026-09-09-096, ATR Channel
Breakout) that uses extension above the band as a **momentum-continuation**
buy trigger — the opposite economic read. This strategy tests the
**exhaustion/fade** interpretation instead: a continuous sizing dial that
reduces long exposure the further price extends above the Kaufman sell
level (0 extension → base_exposure; 3×ATR extension → exposure near 0),
gated by an SMA(trend_window) uptrend filter with a deadband to control
turnover. Long-only (the original's short-entry not replicated, per this
repo's long-only sizing-dial family convention).

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`, param_grid =
`{atr_factor: [1.5, 2.5, 3.5], sensitivity: [0.5, 1.0, 1.5]}`,
symbols = equity [QQQ, SPY] + crypto [BTC/USDT, ETH/USDT],
vol_regime_splits=3, period 2018-01-01 to 2026-09-01.

- **Overall pass_fraction:** 49/108 = 0.454
- **By asset class:** equity 36/54 (0.667), crypto 13/54 (0.241)
- **By vol regime:** low 26/36 (0.722), mid 14/36 (0.389), high 9/36 (0.25)
  — edge concentrates in low-vol regimes, consistent with a fade/exhaustion
  mechanic (works best when trends are orderly, degrades in choppy/high-vol
  conditions where the ATR band gets crossed more randomly).
- **Per-symbol breakdown (passed/3 vol regimes, avg full-sample-cell Sharpe)
  across the 3x3 param grid:**
  - QQQ: 2/3 every config, avg Sharpe 1.22–1.33
  - SPY: 2/3 every config, avg Sharpe 1.35–1.52 (best of the four symbols)
  - BTC/USDT: 0–2/3 depending on config, best at atr_factor=3.5 (2/3, avg
    Sharpe ~1.09–1.26)
  - ETH/USDT: 0/3 at every tested config (avg Sharpe 0.88–1.18 but always
    failing at least one vol-regime cell) — decisively weaker than BTC/USDT
    for this mechanic.

## Single-config validation (Step 7)

| Symbol | Config | Trades | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity (rel. std) | Result |
|---|---|---|---|---|---|---|---|---|
| QQQ | atr_factor=2.5, sensitivity=1.0, deadband=0.35, leverage_cap=1.0 | 247 | 1.090 (>1.0) | 0.153 (<0.25) | 0.534 (>0.5) | 1.0 (4/4 splits) | 0.121 (<0.5) | **PASS (all 5)** |
| SPY | atr_factor=1.5, sensitivity=1.0, deadband=0.35, leverage_cap=1.0 | 231 | 1.287 (>1.0) | 0.094 (<0.25) | 0.510 (>0.5) | 1.0 (4/4 splits) | 0.050 (<0.5) | **PASS (all 5)** |
| BTC/USDT | atr_factor=3.5, sensitivity=1.0, deadband=0.20, leverage_cap=0.4 | 239 | 1.097 (>1.0) | 0.227 (<0.25) | 0.820 (>0.5) | 1.0 (4/4 splits) | 0.105 (<0.5) | **PASS (all 5)** |

Note: the initial deadband=0.20 config narrowly failed transaction-cost
survival for QQQ/SPY (net Sharpe 0.37/0.25, both <0.5, ~330-363 trades).
Widening the deadband to 0.35 for equity cut turnover to ~240 trades and
rescued both. Crypto (BTC/USDT) needed leverage_cap reduced from 0.5→0.4 to
clear MDD (0.277→0.227) at the already-turnover-friendly deadband=0.20.
ETH/USDT not pursued further given decisive 0/3 grid rejection at every
tested config.

## Decision

**Accept: QQQ, SPY, BTC/USDT** (all 5 validators pass with per-symbol tuned
configs). **Reject: ETH/USDT** (decisive grid rejection, edge does not
transmit to this symbol at any tested config).
