# UNG/USO Log-Spread Z-Score Pairs Trade — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ung_uso_spread_zscore_pairs.py`
**KB id:** 2026-09-22-036

## Hypothesis

Per investingwhisperer.com's "THE NATGAS VS. OIL TRADE LONG UNG-NYSE / SHORT
USO-NYSE" (https://investingwhisperer.com/the-natgas-vs-oil-trade-long-ung-nyse-short-uso-nyse/,
read via browser_exec Google SERP fallback — web_search DDGS backend
TLS-erroring on this iteration's queries), natural gas and crude oil
decouple during periods of extreme relative pessimism on one leg (there:
natgas futures curve backwardation). Mechanically operationalized here as a
log(UNG/USO) ratio z-score mean-reversion, long-only single-leg
approximation (no short-USO leg — this repo has no short-selling
infrastructure), following the same template as the already-rejected
ETH/BTC spread pairs trade (2026-09-04-083).

## Grid test (Step 6)

`window` in {20, 30, 45} x `entry_z` in {1.5, 2.0}, symbols
{equity: UNG; crypto: BTC/USDT, ETH/USDT (falsification)}, vol_regime_splits=3.

- Total cells: 54, passed: 0 (**pass_fraction 0.0**)
- by_asset_class: equity 0/18, crypto 0/36
- by_vol_regime: low 0/18, mid 0/18, high 0/18
- best_cell: window=20/entry_z=2.0, UNG, high-vol, Sharpe=1.372 (single-slice artifact, not representative — full-sample fails decisively, see below)
- worst_cell: window=30/entry_z=2.0, UNG, mid-vol, Sharpe=-2.098

## Single-config validation (Step 7) — window=20, entry_z=2.0, exit_z=0.0, stop_z=3.5, max_hold_days=20, UNG, 2019-01-01 to 2026-09-01

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.234 | ≥1.0 | FAIL |
| Max drawdown | 0.392 | ≤0.25 | FAIL |

Decisive rejection on both Sharpe and MDD — no further validators run
(walk-forward/parameter-sensitivity/TC-survival would not change the
outcome given both primary thresholds already fail by a wide margin).

## Decision: REJECTED

Grid pass_fraction 0/54 across every parameter combination, asset class,
and vol regime. UNG's structural roll-decay (consistent with the prior
UNG seasonal strategy 2026-09-13-012's finding of "96.9% MDD... structural
roll-decay swamps seasonal edge") dominates any spread mean-reversion
signal derived from the UNG/USO ratio — MDD 39.2% on the primary config
alone confirms this. Crypto falsification symbols also fail decisively
(0/36), as expected since neither BTC nor ETH has a meaningful USO-ratio
relationship. Consistent with the already-rejected ETH/BTC spread pairs
trade template (2026-09-04-083) — the long-only single-leg approximation
of a genuine market-neutral pairs trade appears to be a structurally weak
construction in this repo generally, now failing on its second test.
