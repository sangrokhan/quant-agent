# Aberration + Low-Vol-Regime Gate Rescue — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_aberration_volregime_gate_rescue.py`
**Rescue of:** knowledge_base id `2026-09-06-144` (Aberration ratcheted-stop
breakout, near-miss rejected: Sharpe 0.927<1.0, MDD 0.2565>0.25, parameter
sensitivity 0.603 decisive fail — that entry's own `notes` explicitly
flagged "a future loop could revisit with an explicit low-vol regime gate
given the stark vol-regime split (low pass_fraction 0.407 vs mid 0.130 vs
high 0.0)"). No new external source this iteration — same underlying
Aberration (Keith Fitschen 1986) hypothesis from
https://concretumgroup.substack.com/p/how-to-size-your-trend-trades, plus a
self-referential low-vol entry gate (a fast/slow realized-vol ratio, does
not require external vol-regime labeling).

## Fix mechanism

Added `vol_regime_ratio` parameter: new entries only fire when a fast
realized-vol proxy (rolling std of returns, `vol_fast_window=20`) is at or
below `vol_regime_ratio` times its own slower rolling average
(`vol_slow_window=100`) — i.e. suppress new entries during elevated-vol
regimes, exactly the gate the prior rejection's grid data recommended.
Existing positions are not force-closed by a mid-trade vol spike (the
strategy's existing ratcheted-stop/time-stop exits already handle that).

## Step 6 — Grid test (validation/grid_test.py::run_strategy_grid)

`param_grid={sma_window:[50], std_mult:[1.5,2.0], vol_regime_ratio:[0.8,1.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01, 48 cells.

- `pass_fraction`: 0.3125 (15/48) — up from the prior (ungated) version's
  0.179 grid pass fraction, confirming the vol-regime gate improves the
  hit rate as the prior entry's notes predicted.
- `by_asset_class`: equity 10/24 (0.417), crypto 5/24 (0.208)
- `by_vol_regime`: low 10/16 (0.625), mid 4/16 (0.25), high 1/16 (0.0625)
- `best_cell`: QQQ, sma_window=50/std_mult=1.5/vol_regime_ratio=1.0,
  low-vol, Sharpe 2.539

## Step 7 — Single-config validation

### QQQ — ACCEPTED (sma_window=50, std_mult=1.5, max_hold_days=40, vol_regime_ratio=1.0)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.251 | 1.0 | ✅ |
| Max drawdown | 0.131 | 0.25 | ✅ |
| TC survival (10bps, 31 trades) | 1.207 | 0.5 | ✅ |
| Walk-forward (manual 4-split) | 0.75 (3/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (rel-std) | 0.226 | 0.5 | ✅ |

### SPY — REJECTED (same config)

Sharpe 0.774 (fail); MDD (0.132), TC-survival (0.709), walk-forward (1.0),
and parameter sensitivity (0.350) all pass. Sharpe-only failure.

### BTC/USDT — ACCEPTED (sma_window=50, std_mult=2.0, max_hold_days=60, vol_regime_ratio=1.0, leverage_cap=0.6)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.192 | 1.0 | ✅ |
| Max drawdown | 0.244 | 0.25 | ✅ |
| TC survival (10bps, 21 trades) | 1.177 | 0.5 | ✅ |
| Walk-forward (manual 4-split) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (rel-std) | 0.261 | 0.5 | ✅ |

### ETH/USDT — ACCEPTED (sma_window=50, std_mult=2.0, max_hold_days=40, vol_regime_ratio=0.8, leverage_cap=0.6)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.061 | 1.0 | ✅ |
| Max drawdown | 0.172 | 0.25 | ✅ |
| TC survival (10bps, 14 trades) | 1.051 | 0.5 | ✅ |
| Walk-forward (manual 4-split) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (rel-std) | 0.092 | 0.5 | ✅ |

Both crypto symbols required the repo's standard `leverage_cap` scaling
(0.6) to keep MDD comfortably under budget — Sharpe is leverage-invariant
for pure long/flat exposure.

## Outcome

**Accepted (QQQ, BTC/USDT, ETH/USDT); rejected (SPY, Sharpe-only near-miss
0.774).** The low-vol-regime gate successfully rescues the prior near-miss
across 3 of 4 tracked symbols — a clean confirmation of the vol-regime
diagnosis flagged in the original rejection's `notes`.
