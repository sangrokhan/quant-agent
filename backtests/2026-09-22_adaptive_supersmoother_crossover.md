# Backtest Report: Ehlers Adaptive SuperSmoother Crossover (TASC Sep 2026)

**Strategy file:** `strategies/2026-09-22_adaptive_supersmoother_crossover.py`
**Date:** 2026-09-22
**Outcome:** REJECTED

## Hypothesis

Per John F. Ehlers' "Improved Filter Performance" (TASC Traders' Tips,
September 2026), replicated exactly per the TradingView editors'-pick port
(https://www.tradingview.com/script/FnlMn99W-TASC-2026-09-Adaptive-SuperSmoother/,
read via browser_exec this iteration), a fixed-period 2-pole SuperSmoother
low-pass filter's own 1-bar ROC (RMS-normalized, capped at 2.0) drives a
second SuperSmoother's critical period adaptively (period shrinks when the
fixed filter is changing quickly relative to its own recent RMS). Source's
disclosed rule: long when the Adaptive SuperSmoother is above the
fixed-period SuperSmoother, short (flat, long-only here) otherwise.

Distinct from this repo's 5+ prior Ehlers-SuperSmoother-based entries
(MESA Stochastic, Roofing Filter, Trendflex, Even Better Sinewave,
Reflex) -- none implement Ehlers' specific adaptive-period construction
or its disclosed adaptive-vs-fixed crossover rule.

## Step 6 — Grid test summary

Grid: `base_period` ∈ {15,20,25}, `max_hold_days` ∈ {40,60} × symbols
{QQQ, SPY} (equity) / {BTC/USDT, ETH/USDT} (crypto) × 3 vol-regime
terciles = 72 cells, 2019-01-01 to 2026-09-01.

```
pass_fraction: 0.25 (18/72)
by_asset_class: equity 18/36 passed, crypto 0/36 passed
by_vol_regime:  low 12/24, mid 6/24, high 0/24
best_cell: base_period=15, max_hold_days=40, QQQ, low-vol regime, Sharpe=2.16
worst_cell: base_period=15, max_hold_days=60, ETH/USDT, high-vol regime, Sharpe=-0.004
```

## Step 7 — Full-sample validators (best config: QQQ, base_period=15,
rms_length=81, max_hold_days=40, full sample 2019-2026)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.885 | >= 1.0 | FAIL |
| Max drawdown | 30.2% | <= 25% | FAIL |
| Transaction cost survival (10 bps/trade, 75 trades) | 0.822 net Sharpe | >= 0.5 | PASS |
| Walk-forward (manual 4-split) | 3/4 splits positive (0.75) | >= 0.75 | PASS (borderline) |
| Parameter sensitivity (6-point grid, relative std) | 0.128 | <= 0.5 | PASS |

## Step 8 — Decision: REJECTED

Same pattern as the earlier DiNapoli attempt this cron trigger: the
grid's best cell (low-vol regime only) does not generalize -- full-sample
Sharpe (0.885) and drawdown (30.2%) both fail this repo's thresholds,
even though cost-survival, walk-forward, and parameter sensitivity pass.
The strategy's edge is concentrated in low-vol equity regimes and does
not hold up broadly; crypto fails outright across all regimes.

## Source

https://www.tradingview.com/script/FnlMn99W-TASC-2026-09-Adaptive-SuperSmoother/
