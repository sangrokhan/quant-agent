# Qstick Bullish Divergence, Low-Vol-Regime-Gated — Backtest Report (near-miss rescue attempt)

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_qstick_bullish_divergence_lowvol_gate.py`
**Follow-up to:** 2026-09-09-088 (plain Qstick bullish divergence, rejected — full-sample Sharpe QQQ -0.249, SPY 0.112; notes explicitly flagged edge concentrated in low-vol regime, Sharpe 2.07 in that slice)

## Hypothesis

2026-09-09-088's own grid data + notes explicitly recommended gating this
signal to the low-vol tercile, following this repo's established
`2026-09-03_bb_meanrev_qqq_volregime.py` pattern. This iteration
implements that fix: adds a realized-vol regime AND-gate + risk-off exit
on regime flip.

## Grid test summary (qstick_window∈{10,14,20} × swing_lookback∈{15,20} × vol_regime_ratio∈{0.9,1.0,1.2}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 216, passed_cells: 22, pass_fraction: 0.102
- by_asset_class: equity 9/108; crypto 13/108
- by_vol_regime: low 8/72; mid 5/72; high 9/72 (no longer strongly regime-concentrated after gating -- the gate reshapes but doesn't dramatically improve overall pass rate)
- Best symbol-level configs: ETH/USDT qstick_window=14/swing_lookback=15/vol_regime_ratio=0.9 (avg Sharpe 0.680); QQQ qstick_window=14/swing_lookback=20/vol_regime_ratio=0.9 (avg Sharpe 0.928, 1/3 regime slices passed)

## Single-config validation

| Symbol (config) | Sharpe | MDD | TC-survival | Walk-forward (manual fallback*) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ (qstick_window=14, swing_lookback=20, vol_regime_ratio=0.9) | 0.737 (FAIL, thr 1.0) | 0.023 (PASS) | 0.722 (PASS) | 1.0 (PASS) | 5.941 (FAIL -- only 2 trades total, degenerate) |
| ETH/USDT (qstick_window=14, swing_lookback=15, vol_regime_ratio=0.9) | 0.756 (FAIL, thr 1.0) | 0.247 (PASS, near threshold) | 0.728 (PASS) | 0.75 (PASS) | 0.457 (PASS) |

\* Same known repo `vbt.utils.splitting.RangeSplitter` API issue — manual 4-way chronological split fallback used.

## Decision: **REJECT**

QQQ's best config only fires 2 trades over the full 2019-2026 sample —
degenerate/overfit to a couple of lucky occurrences, confirmed by the
absurd 5.94 parameter-sensitivity relative-std (the strategy's Sharpe
swings wildly across the param grid because there's barely any signal to
begin with under this AND-gate). ETH/USDT is a genuine near-miss: 4 of 5
validators pass cleanly (MDD, TC-survival, walk-forward, parameter
sensitivity all comfortably pass) and only Sharpe falls short (0.756 vs
1.0) — a real, stable, if modest, improvement over the ungated version's
0/108 crypto grid pass rate. This is the strongest signal yet that the
low-vol-gate direction is right but the current parameterization
undershoots the Sharpe bar; a future iteration could widen the crypto
grid search (different `qstick_window`/`swing_lookback` combos, or a
tighter `vol_regime_ratio`) specifically targeting ETH/USDT rather than
trying to force a shared equity+crypto config.
