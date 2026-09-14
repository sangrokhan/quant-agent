# Andean Oscillator Bull-Bear Net Pressure Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-160 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_andean_bullbear_sizing_sma_trend.py`

## Hypothesis

Andean Oscillator (Alex Grover, 2022; per Google AI-overview cross-referencing
Alpaca/ProRealCode/TakeProfit — `web_search`'s DDG backend failed for this
query with a TLS connection error, `browser_exec` Google search fallback
used): two one-directional ratchet exponential envelopes around price and
price², producing Bull/Bear "standard deviation vs envelope" components.
Repo has exactly 1 prior Andean Oscillator entry (2026-09-05-016, a binary
EMA-signal-line crossover trigger). This iteration reframes the indicator's
own net pressure (Bull − Bear), normalized by close price, as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], sized within an
SMA(trend_window) uptrend gate, deadband + leverage_cap for crypto. First
Andean Oscillator continuous-sizing variant.

Source: https://www.prorealcode.com/prorealtime-indicators/andean-oscillator/
(full formula + reference ProRealTime code), cross-checked against a Google
AI-overview summary (via browser_exec fallback) citing Alpaca/TakeProfit for
interpretation.

## Grid test summary (Step 6)

`param_grid={andean_length: [30,50,80], sensitivity: [0.4,0.6,0.8],
leverage_cap: [0.4,1.0]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3.

- **total_cells:** 216, **passed:** 112, **pass_fraction:** 0.519.
- **by_asset_class:** equity 60/108 (0.556), crypto 52/108 (0.481).
- **by_vol_regime:** low 59/72 (0.819), mid 38/72 (0.528), high 15/72 (0.208)
  — clear degradation in high-vol regimes, consistent with most prior
  trend-gated sizing overlays this cron trigger.
- **best_cell:** QQQ, andean_length=50/sensitivity=0.4/leverage_cap=1.0,
  low-vol, Sharpe 3.153.
- **worst_cell:** QQQ, andean_length=80/sensitivity=0.6/leverage_cap=0.4,
  high-vol, Sharpe -0.668.

## Single-config validator results (Step 7)

Best grid config (andean_length=50, sensitivity=0.4) tested per symbol,
leverage_cap=1.0 (equity) / 0.4 (crypto), manual 4-fold walk-forward split
(vectorbt 1.1.0 lacks `vbt.utils.splitting.RangeSplitter`, consistent with
prior iterations' documented workaround), parameter sensitivity from a
5-point sweep of `sensitivity` in [0.3, 0.4, 0.5, 0.6, 0.8]:

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.241 (pass) | 0.134 (pass) | 1.081 (pass) | 0.750 (pass) | 0.030 (pass) | **accepted** |
| SPY | 1.032 (pass) | 0.097 (pass) | 0.845 (pass) | 0.750 (pass) | 0.009 (pass) | **accepted** |
| BTC/USDT | 0.128 (**fail**, thr 1.0) | 0.278 (**fail**, thr 0.25) | -0.051 (**fail**, thr 0.5) | 0.750 (pass) | 0.057 (pass) | **rejected** |
| ETH/USDT | 0.196 (**fail**, thr 1.0) | 0.307 (**fail**, thr 0.25) | -0.030 (**fail**, thr 0.5) | 1.000 (pass) | 0.023 (pass) | **rejected** |

## Decision

**Accepted (equity only):** QQQ, SPY — all 5 validators pass with
comfortable margins even at leverage_cap=1.0 (no leverage reduction
needed).
**Rejected (crypto):** BTC/USDT, ETH/USDT — decisive failure on Sharpe, MDD,
AND TC-survival simultaneously even at reduced leverage_cap=0.4; unlike
several prior cron-trigger entries this cron trigger, lowering crypto
leverage does not rescue this indicator since the underlying Sharpe is
already near zero (leverage_cap only clips exposure upside, it does not
uniformly rescale realized Sharpe). Andean Oscillator's ratchet-envelope
construction appears to track equity trend persistence well but produces a
noisy/whipsawing net-pressure signal on 24/7 crypto price action.
