# Fibonacci Fan, Low-Vol-Regime-Gated — Backtest Report (near-miss rescue attempt)

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_fibonacci_fan_lowvol_regime_gate.py`
**Follow-up to:** 2026-09-28-040 (plain Fibonacci Fan breakout, rejected — full-sample Sharpe SPY 0.872, QQQ -0.352)

## Hypothesis

2026-09-28-040's own grid test showed the Fibonacci Fan breakout edge is
real but concentrated in low-volatility regimes (by_vol_regime pass rate:
low 13/48, mid 9/48, high 3/48 — monotonic decay with volatility). This
iteration adds an explicit realized-vol regime AND-gate (20d realized vol
<= vol_regime_ratio x its own trailing 252d median), matching this repo's
established Bollinger-mean-reversion vol-gate pattern
(`strategies/2026-09-03_bb_meanrev_qqq_volregime.py`), plus a risk-off exit
when the regime flips to high-vol mid-trade.

## Grid test summary (swing_lookback∈{40,60,90} × upper_ratio∈{0.5,0.618} × vol_regime_ratio∈{0.9,1.0,1.2}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 216, passed_cells: 24, pass_fraction: 0.111
- by_asset_class: equity 15/108; crypto 9/108
- by_vol_regime: low 7/72; mid 9/72; high 8/72 (regime gate successfully flattens the high-vol decay seen in the ungated version — good sign the gate is doing its job, though overall pass_fraction dropped slightly vs. ungated 0.174 because trading opportunities shrink)
- best_cell: SPY, swing_lookback=40, upper_ratio=0.5, vol_regime_ratio=1.2, low-vol regime, Sharpe 1.986 (same peak as ungated version)
- Best full-sample-weighted config found by symbol-level aggregation: SPY swing_lookback=40/upper_ratio=0.5/vol_regime_ratio=1.2, avg Sharpe 1.526 (vs 0.872 full-sample Sharpe for the ungated version — meaningful improvement)

## Single-config validation (swing_lookback=40, upper_ratio=0.5, vol_regime_ratio=1.2, max_hold_days=15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward (manual fallback*) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| SPY | 1.245 (PASS, thr 1.0) | 0.032 (PASS, thr 0.25) | 0.990 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | **1.066 (FAIL, thr 0.5)** |
| QQQ | -0.234 (FAIL) | 0.098 (PASS) | -0.324 (FAIL) | 0.5 (FAIL) | 1.336 (FAIL) |

\* Same known repo `vbt.utils.splitting.RangeSplitter` API issue as
2026-09-28-040 — manual 4-way chronological split fallback used.

## Decision: **REJECT**

The vol-regime gate successfully rescued SPY's Sharpe (0.872 → 1.245,
now passing) and its TC-survival/walk-forward now pass cleanly, but
**parameter sensitivity fails decisively (1.066 vs 0.5 threshold)** — the
grid's per-cell Sharpe values for SPY swing between roughly -0.3 and 1.9
across the 18-cell param sweep (swing_lookback × upper_ratio ×
vol_regime_ratio), meaning the improvement is fragile to the exact
parameter choice rather than a robust edge. QQQ remains a decisive fail
across every validator. This confirms the underlying signal (fan-line
breakout) genuinely benefits from a vol-regime gate directionally, but
the specific parameterization tested here is not stable enough to accept.
A future iteration could try a coarser/more-robust param grid (e.g. only
2 param dimensions instead of 3, or a wider swing_lookback net) rather
than the current instability.
