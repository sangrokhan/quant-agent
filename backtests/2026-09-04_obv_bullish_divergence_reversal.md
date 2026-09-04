# OBV Bullish Divergence Reversal + EMA Crossback Trigger — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_obv_bullish_divergence_reversal.py`
**Outcome:** REJECTED

## Hypothesis

Per arrowalgo.com's mechanical OBV divergence rule set: a bullish
divergence occurs when price makes a new N-bar low while On-Balance
Volume does NOT make a new N-bar low (selling pressure drying up even as
price slips) -- a setup, not a trigger. The mechanical trigger is price
closing back above a short EMA; stop below the divergence low. Distinct
from 2026-09-04-027 (OBV as a simple confirmation filter on a separate
breakout signal) -- this is a genuine two-series rolling-extreme
divergence comparison with its own trigger.

Source: https://arrowalgo.com/obv-divergence-strategy/ (found via
`web_search`, which succeeded this iteration; `web_extract` failed on the
same URL with a DDGS-backend-limitation error, fell back to
`browser_exec`).

## Grid test summary (window x ema_window x max_hold_days, 2 equity + 2
crypto symbols, 3 vol regimes)

- total_cells: 96, passed_cells: 12, **pass_fraction: 0.125**
- by_asset_class: equity 12/48, crypto **0/48**
- by_vol_regime: low 4/32, mid 5/32, high 3/32
- best_cell: SPY, window=30/ema_window=20/max_hold_days=20, low-vol
  regime, Sharpe 2.27

## Full-sample Sharpe by config (equity only)

| config | QQQ | SPY |
|---|---|---|
| window=30, ema=20, hold=20 | 0.508 | 0.657 |
| window=40, ema=10, hold=20 | 0.411 | 0.239 |
| window=30, ema=10, hold=10 | 0.390 | 0.087 |

## Single-config validators (primary config: SPY, window=30,
ema_window=20, lookahead=10, max_hold_days=20 — best full-sample config
found)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.657 | 1.0 |
| max_drawdown | pass | 0.076 | 0.25 |
| transaction_cost_survival | pass | 0.568 (net Sharpe after costs) | 0.5 |

Only 20 round-trip trades over 7.7yr — very low frequency (the
divergence + EMA-crossback double-condition is quite selective) — MDD is
the best (0.076) of any strategy tested this session, but the underlying
edge (Sharpe) never approaches 1.0 on either equity symbol.

## Decision

**Rejected.** No config on QQQ or SPY reaches the 1.0 Sharpe threshold
(best: SPY 0.657). Grid pass_fraction low (0.125, 12/96) — the double
divergence-plus-confirmation condition is too rare/selective to generate
a reliable edge at this trade frequency (only 20 trades on the best
config), consistent with the source's own explicit caveat that
divergence "does not time reversals precisely" and is "stronger as a
filter/warning than a standalone trigger" -- exactly what this repo's
own -027 (OBV as filter) already tested and found workable in
combination with a separate signal, while divergence as the PRIMARY
signal (this strategy) does not clear the bar alone. Crypto rejected
decisively (0/48 grid cells). Not implemented as a live strategy.
