# Backtest Report: Percent-Away Deviation Band Mean Reversion with Trend Filter

**Strategy file:** `strategies/2026-09-21_pct_deviation_band_meanrev_trend.py`
**Date:** 2026-09-21
**Hypothesis source:** Google AI-overview synthesis of QuantVero/VT
Markets/LuneFi mean-reversion guides (dip below a %-deviation band from a
50-day SMA baseline, gated by a 200-day SMA trend filter, exit at the
baseline or an ATR stop).

## Hypothesis

A percentage-deviation band around a 50-day SMA baseline (±3.5%/±7.0%),
combined with a 200-day SMA trend filter, identifies mean-reversion
pullbacks IN THE DIRECTION of the dominant trend. Long entry: price dips
below the lower band then closes back inside it, while still above the
200-SMA. Exit at the SMA baseline (mean-reversion target) or an ATR
stop-loss. Distinct from the already-rejected Kairi Relative Index
(2026-09-04-167, similar %-deviation concept) via its 2-bar
dip-then-recover confirmation and price-target exit mechanic (vs KRI's
oscillator-threshold exit).

## Grid test (Step 6)

`param_grid={"dev_pct": [0.035, 0.07], "stop_atr_mult": [1.5, 2.0],
"max_hold_days": [10, 20]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, period 2018-01-01 to
2026-09-01.

- Overall pass_fraction: 13/96 = 0.135
- By asset class: equity 13/48, crypto 0/48 (decisive crypto reject)
- By vol regime: low 0/32, mid 3/32, high 10/32

## Full-sample single-config sweep

QQQ: Sharpe range 0.813-0.941 (all FAIL, closest near-miss 0.941 at
dev_pct=0.035/stop_atr_mult=2.0/max_hold_days=20), MDD comfortably passes
(0.062-0.077).

SPY: Sharpe 0.189-0.202 at dev_pct=0.035 (decisive fail); at dev_pct=0.07,
**zero trades fire at all** (band too wide for SPY's typical volatility
range, giving a degenerate Sharpe=inf/MDD=0 artifact from an all-zero
return series — not a genuine pass).

BTC/USDT: Sharpe range -0.454 to 0.393, all FAIL, MDD often exceeds 0.25.
ETH/USDT: Sharpe range -0.173 to 0.056, all FAIL, MDD 0.36-0.46.

## Decision: REJECTED

QQQ comes closest (Sharpe 0.941, just under the 1.0 threshold) but no
config passes cleanly. SPY's apparent "pass" is a degenerate zero-trade
artifact, not real performance. Crypto rejected decisively across the
board. This specific dip-then-recover + baseline-target mechanic does not
clear this repo's bar on any tested symbol.
