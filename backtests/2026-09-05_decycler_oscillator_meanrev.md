# Ehlers Decycler Oscillator Countertrend Mean-Reversion — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_decycler_oscillator_meanrev.py`
**Knowledge base id:** 2026-09-05-046

## Hypothesis

John Ehlers' Decycler Oscillator (percentage spread between a fast and a
slow 2-pole-highpass-filtered "Decycler" trend line) signals oversold/
overbought extremes when the fast decycler pulls too far from the slow
one. Per a Google SERP snippet of theindicatorlab.com's Decycler review
(direct fetch 404'd; browser fallback used, snippet only — see notes):
"Long entry: Oscillator crosses above -50 after being below -80
(oversold condition). Short entry: Oscillator crosses below +50 after
being above +80." Implemented long-only: enter on the oversold snapback
cross, exit on the overbought snapback cross or a `max_hold_days`
time-stop.

Source: Google SERP for `"Ehlers_Decycler Review" "Long entry" "Short
entry" oscillator crosses` (theindicatorlab.com result); direct
`browser_exec` fetch of the article URL returned a 404 "Not Found" page,
so only the SERP snippet's threshold levels (-80/-50/+50/+80) could be
grounded — the exact oscillator scaling formula is our own
reconstruction (`osc_scale`-normalized dual-highpass percentage spread),
flagged honestly rather than presented as verbatim-sourced.

## Grid test summary (Step 6)

`validation/grid_test.py::run_strategy_grid`, param grid
`hp_fast_period=[20,30,40] x hp_slow_period=[50,60,80] x osc_scale=[15,20,25]`,
symbols `equity=[QQQ,SPY]`, `crypto=[BTC/USDT,ETH/USDT]`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01. **324 cells total.**

- **pass_fraction: 0.0154** (5 / 324 cells passed both Sharpe>=1.0 and MDD<=0.25)
- by_asset_class: equity 5/162 passed; **crypto 0/162 passed** (rejected outright)
- by_vol_regime: low 1/108; mid 0/108; **high 4/108** (only narrow high-vol slices passed)
- best_cell: `hp_fast_period=20, hp_slow_period=80, osc_scale=25.0`, QQQ, low-vol tercile, Sharpe 1.78
- worst_cell: `hp_fast_period=30, hp_slow_period=80, osc_scale=25.0`, QQQ, mid-vol tercile, Sharpe -0.87

## Single-config validation (Step 7) — best config, QQQ, full period 2019-2026

Config: `hp_fast_period=20, hp_slow_period=80, osc_scale=25.0` (grid's best cell's params, run over the FULL period rather than just the low-vol tercile slice that produced the 1.78 Sharpe).

| Validator | Result | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ FAIL | 0.38 | >= 1.0 |
| max_drawdown | ✅ pass | 0.234 | <= 0.25 |
| transaction_cost_survival (10bps/trade, 22 trades) | ❌ FAIL | 0.35 | >= 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ❌ FAIL | 2/4 splits positive (0.5 pass fraction) | >= 0.75 |

## Decision: **REJECTED**

Full-period Sharpe (0.38) collapses relative to the grid's best isolated
cell (1.78, only the low-vol tercile of QQQ) — a classic case of a narrow
slice looking attractive while the full-period/broad-grid picture is
decisively unfavorable (1.5% overall pass fraction, 0/162 on crypto
entirely). Transaction costs and walk-forward both fail as well. Not a
near-miss worth revisiting without materially rethinking the
oscillator's scaling/thresholds.
