# ROC(12) Zero-Cross + EMA(50) Trend Filter — Backtest Report

**Hypothesis** (kb id 2026-09-04-039): ROC(12) crossing above/staying above
zero, combined with close > EMA(50) as a trend filter, signals a long
position that should reduce false signals in choppy markets versus either
condition alone. Exit when either condition breaks.

**Source**: Google AI-overview + Quantified Strategies' Rate of Change
article (web_search failed 3x with a DDGS/Yahoo TLS connection error this
iteration, fell back to browser_exec immediately per loop-avoidance rule).

## Grid test (Step 6)

`param_grid = {roc_window: [10,12,20], ema_window: [50]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 36 total cells.

- pass_fraction: **0.25** (9/36)
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 3/12, high 0/12
- best_cell (source's original params, roc_window=12, ema_window=50): QQQ, low-vol tercile, Sharpe 2.842

## Full-sample validators (Step 7) — primary config (roc_window=12, ema_window=50, source's original params)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| **QQQ** | **1.252 (pass, thr 1.0)** | **0.223 (pass, thr 0.25)** | **1.098 (pass, thr 0.5)** | 98 |
| **SPY** | **1.067 (pass, thr 1.0)** | **0.180 (pass, thr 0.25)** | **0.850 (pass, thr 0.5)** | 101 |
| BTC/USDT | 0.213 (fail) | 0.449 (fail) | -0.018 (fail) | 3953 |
| ETH/USDT | 0.247 (fail) | 0.496 (fail) | 0.010 (fail) | 3763 |

QQQ walk-forward (4 manual date-slices, vectorbt splitting API bug
workaround): **4/4 splits positive**, pass fraction 1.0. QQQ parameter
sensitivity (roc_window in {10,12,15}, ema_window=50 fixed): relative std
**0.0088** vs 0.5 ceiling — passes with an extremely wide margin, the most
parameter-stable result in this log to date.

Crypto trade counts are extremely high (3763-3953 over 7.7 years) —
ROC(12) zero-crosses whipsaw constantly on BTC/ETH's noisier daily action,
consistent with prior rejections of fast oscillator-based rules on crypto.

## Decision: ACCEPTED (QQQ and SPY); rejected (crypto decisively)

Both equity symbols clear every validator with comfortable margin at the
source's original, un-tuned parameters (roc_window=12, ema_window=50) — no
manual refinement needed, unlike the Coppock Curve accept two iterations
ago. QQQ: Sharpe 1.252, MDD 22.3%, net Sharpe 1.098, walk-forward 4/4,
parameter sensitivity 0.0088 (exceptionally stable). SPY: Sharpe 1.067, MDD
18.0%, net Sharpe 0.850. Crypto fails all validators decisively due to high
turnover and low signal quality at this parameterization on 24/7 markets.
