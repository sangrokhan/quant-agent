# Backtest Report: ICT "Unicorn" Model — Breaker Block + FVG Overlap Entry

**Strategy file:** `strategies/2026-09-24_ict_unicorn_breaker_fvg_overlap.py`
**Date:** 2026-09-24
**Source:** LuxAlgo Smart Money Concepts / ICT library, "Unicorn" concept page
(https://www.luxalgo.com/library/concept/unicorn/, read via browser_exec
after web_search DDGS backend intermittently failed/returned stale results
this iteration).

## Hypothesis

A bullish Unicorn setup is a 5-step ICT confluence: (1) a liquidity sweep
below a prior swing low that recovers, (2) a displacement move breaking the
prior swing high that leaves a bullish 3-candle Fair Value Gap, (3) a
"breaker block" (the down-leg bar that made the swept swing low), (4) the
geometric overlap between the breaker's price range and the FVG's price
range, and (5) entry on a retrace back into that overlap, invalidated by a
close below the breaker's low. Operationalized here on daily bars (no
session/killzone filter, since data/loaders.py provides daily OHLCV only).

## Grid Test Summary (Step 6)

`param_grid={"swing_window": [3,5,8], "displacement_window": [8,15],
"take_profit_atr_mult": [2.0,3.0,4.0]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction:** 0.375 (81/216)
- **by_asset_class:** equity 41/108 (38%), crypto 40/108 (37%) — genuinely
  broad, not equity-only like most strategies in this repo.
- **by_vol_regime:** low 34/72 (47%), mid 28/72 (39%), high 19/72 (26%) —
  holds up across regimes better than most strategies here.
- **best_cell:** SPY low-vol, swing_window=3/displacement_window=8/
  take_profit_atr_mult=3.0, Sharpe=2.514.
- **worst_cell:** SPY mid-vol, swing_window=5/displacement_window=15/
  take_profit_atr_mult=3.0, Sharpe=-0.975.

## Single-Config Validation (Step 7)

Config: `swing_window=3, displacement_window=8, take_profit_atr_mult=3.0`
(the grid's clear best-performing combination), full 2019-2026 sample.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | **1.184** (pass) | 0.078 (pass) | 1.109 (pass, 30 trades) | 1.0 (4/4, pass) | 0.392 (pass) |
| SPY | **1.012** (pass) | 0.082 (pass) | 0.939 (pass, 24 trades) | 1.0 (4/4, pass) | 0.655 (**fail**, threshold 0.5) |
| BTC/USDT | 0.557 (fail) | 0.182 (pass) | 0.283 (fail, 605 trades) | — | — |
| ETH/USDT | 0.593 (fail) | 0.133 (pass) | 0.363 (fail, 601 trades) | — | — |

Crypto's much higher trade count (600+ vs 24-30 for equity) at the same
parameters indicates the daily-bar swing/sweep/FVG detection fires far more
often on crypto's noisier 24/7 price action, degrading the signal and
crushing transaction-cost survival.

## Decision

**Accept QQQ** (all 5 validators pass). **SPY is a genuine near-miss**
(4/5 pass, only parameter sensitivity narrowly fails at 0.655 vs 0.5
threshold — the Sharpe swings from 2.51 at the best config down toward
weaker/negative values at other swing_window/displacement_window
combinations, more so than QQQ). Crypto (BTC/USDT, ETH/USDT) is **rejected
decisively** — Sharpe and transaction-cost survival fail on both, driven by
excessive signal frequency on 24/7 markets.
